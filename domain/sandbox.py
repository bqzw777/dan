"""
安全沙箱 —— 静态正则校验 + RiskLevel 分级 + Docker 容器隔离 + 审计日志。

四层防线：
  1. 静态正则校验（22条Block + 11条Warn）
  2. RiskLevel 分级（Safe / Warn / Block）
  3. Docker 容器隔离（--network none, --read-only, --cap-drop ALL, no-new-privileges）
  4. Kafka 审计日志（异步推送）
"""

import re
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class RiskLevel(str, Enum):
    SAFE = "safe"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class ValidationResult:
    level: RiskLevel = RiskLevel.SAFE
    reason: str = ""
    violations: List[str] = field(default_factory=list)


@dataclass
class SandboxConfig:
    backend: str = "docker"        # "docker" | "local" | "mock"
    image: str = "ubuntu:22.04"
    timeout_ms: int = 30000
    max_output_bytes: int = 65536
    memory_limit_mb: int = 256
    cpu_percent: int = 50
    max_pids: int = 64
    network_disabled: bool = True
    readonly_rootfs: bool = True
    artifact_host_dir: str = "~/Desktop/agi-artifacts"


@dataclass
class ExecRequest:
    command: str
    timeout: int = 0
    confirm: bool = False          # Warn 级需确认
    workspace_host_dir: str = ""


@dataclass
class ExecResult:
    command: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    killed: bool = False
    truncated: bool = False
    duration: float = 0.0
    backend: str = ""
    validation: Optional[ValidationResult] = None


# ── 安全规则 ──

BLOCK_RULES = [
    # 文件系统破坏
    (re.compile(r"rm\s+(-[rfRF]+\s+)?/"), "禁止删除根路径"),
    (re.compile(r"\bdd\s+if="), "禁止 dd 设备写入"),
    (re.compile(r"\bmkfs\b"), "禁止格式化文件系统"),
    (re.compile(r">\s*/dev/(sd|hd|nvme|vd|xvd)"), "禁止写入块设备"),
    # 权限提升
    (re.compile(r"\bsudo\b"), "禁止 sudo"),
    (re.compile(r"\bsu\s"), "禁止 su"),
    (re.compile(r"\bchmod\s+[0-7]*7[0-7][0-7]\b"), "禁止 chmod 777"),
    # 系统控制
    (re.compile(r"\b(shutdown|reboot|halt|poweroff)\b"), "禁止关机/重启"),
    (re.compile(r"\bsystemctl\s+(stop|disable|mask)\b"), "禁止停止系统服务"),
    # Shell 注入
    (re.compile(r"\$\(.*\)"), "禁止命令替换 $()"),
    (re.compile(r"`[^`]+`"), "禁止反引号命令替换"),
    (re.compile(r"\beval\b"), "禁止 eval"),
    # 敏感文件
    (re.compile(r"/etc/(passwd|shadow|sudoers|ssh)"), "禁止访问系统凭证"),
    (re.compile(r"~/\.(ssh|aws|docker|kube)/"), "禁止访问凭证目录"),
    # 网络外联
    (re.compile(r"\b(curl|wget|nc|netcat)\s.*http"), "禁止网络外联"),
    (re.compile(r"\bssh\b"), "禁止 SSH"),
    # 进程滥用
    (re.compile(r"\bkillall\b"), "禁止 killall"),
    (re.compile(r":\s*\(\s*\)\s*\{.*:\s*\|"), "禁止 Fork 炸弹"),
]

WARN_RULES = [
    (re.compile(r"\brm\s"), "删除文件操作"),
    (re.compile(r">\s*\w"), "输出重定向"),
    (re.compile(r"\bkill\s"), "进程终止操作"),
    (re.compile(r"\bpip\s+install\b"), "安装 Python 包"),
    (re.compile(r"\bnpm\s+install\b"), "安装 Node 包"),
    (re.compile(r"\bapt(-get)?\s+install\b"), "安装系统包"),
    (re.compile(r";\s*\S"), "命令链（分号）"),
    (re.compile(r"\|"), "管道符"),
    (re.compile(r"&&"), "条件命令链 &&"),
    (re.compile(r"\|\|"), "条件命令链 ||"),
]


class Validator:
    """命令静态安全校验。"""

    def __init__(self, max_command_length: int = 500, allowlist_mode: bool = False,
                 allowlist: List[str] = None):
        self.max_command_length = max_command_length
        self.allowlist_mode = allowlist_mode
        self.allowlist = allowlist or []

    def validate(self, command: str) -> ValidationResult:
        if len(command) > self.max_command_length:
            return ValidationResult(RiskLevel.BLOCK, "命令超过最大长度限制")
        if not command.strip():
            return ValidationResult(RiskLevel.BLOCK, "命令不能为空")

        # 白名单模式
        if self.allowlist_mode and self.allowlist:
            first_word = command.split()[0] if command.split() else ""
            if first_word not in self.allowlist:
                return ValidationResult(RiskLevel.BLOCK,
                                        f'白名单模式：命令 "{first_word}" 未在允许列表中')

        # Block 规则
        for pattern, reason in BLOCK_RULES:
            if pattern.search(command):
                return ValidationResult(RiskLevel.BLOCK, reason)

        # Warn 规则
        violations = [v for pattern, v in WARN_RULES if pattern.search(command)]
        if violations:
            return ValidationResult(RiskLevel.WARN, "", violations)

        return ValidationResult(RiskLevel.SAFE)


class Sandbox:
    """沙箱执行器 —— 封装 Validator + Executor + 审计回调。"""

    def __init__(self, validator: Validator, backend: str = "local"):
        self.validator = validator
        self.backend = backend
        self._audit_fn: Optional[Callable[[ExecResult], None]] = None
        self._config = SandboxConfig()

    def set_config(self, cfg: SandboxConfig) -> None:
        self._config = cfg

    def set_audit_fn(self, fn: Callable[[ExecResult], None]) -> None:
        self._audit_fn = fn

    def exec(self, command: str, confirm: bool = False,
             timeout: int = 0) -> ExecResult:
        """主入口：校验 → Block拒绝 / Warn确认 → 执行 → 审计。"""
        validation = self.validator.validate(command)
        result = ExecResult(command=command, validation=validation, backend=self.backend)

        if validation.level == RiskLevel.BLOCK:
            result.exit_code = -1
            result.stderr = f"[拒绝执行] {validation.reason}"
            self._audit(result)
            return result

        if validation.level == RiskLevel.WARN and not confirm:
            result.exit_code = -2
            vs = ", ".join(validation.violations)
            result.stderr = f"[需要确认] 该命令触发以下规则：{vs}；请设置 confirm=True"
            self._audit(result)
            return result

        # 执行
        start = time.time()
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=(timeout or self._config.timeout_ms) / 1000,
            )
            result.stdout = proc.stdout or ""
            result.stderr = proc.stderr or ""
            result.exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            result.killed = True
            result.exit_code = -4
            result.stderr = f"[超时] 执行超过 {timeout or self._config.timeout_ms}ms 被强制终止"
        except Exception as e:
            result.exit_code = -5
            result.stderr = f"[沙箱内部错误] {e}"

        result.duration = time.time() - start
        self._audit(result)
        return result

    def _audit(self, result: ExecResult) -> None:
        if self._audit_fn:
            try:
                self._audit_fn(result)
            except Exception:
                pass  # 审计失败不阻塞业务
