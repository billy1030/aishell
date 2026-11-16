"""Pydantic data schema representing inspected host system context."""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class SystemContext(BaseModel):
    """Host environment facts discovered by system inspector per D-01 and CTXT-01."""

    os_name: str = Field(..., description="Operating system distribution name (e.g. Ubuntu, Fedora, Debian)")
    os_version: str = Field(..., description="Operating system distribution version (e.g. 24.04, 39)")
    os_family: str = Field(..., description="OS distribution family/like (e.g. debian, rhel, arch, alpine)")
    kernel: str = Field(..., description="Linux kernel release or system version")
    arch: str = Field(..., description="Hardware architecture (e.g. x86_64, aarch64)")
    cwd: str = Field(..., description="Current working directory path")
    user: str = Field(..., description="Active user login name")
    is_root: bool = Field(default=False, description="Whether active user has root/administrative privileges")
    shell: str = Field(default="/bin/bash", description="Active or default user shell binary")
    package_manager: str = Field(default="unknown", description="Detected primary package manager (apt, dnf, pacman, apk, zypper)")
    git_branch: Optional[str] = Field(default=None, description="Active git branch if inside a git repository")
    git_clean: Optional[bool] = Field(default=None, description="Whether git working tree is clean without uncommitted changes")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Sanitized allowlist-filtered environment variables")
