"""Sanitizer encapsulating host environment observations inside untrusted boundary tags."""

from aishell.context.schema import SystemContext


def sanitize_boundary_text(text: str) -> str:
    """Neutralize boundary breakout and injection attempts by escaping XML-like tags."""
    if not text:
        return ""
    # Escape observation boundary tags
    sanitized = text.replace("</system_observation>", "&lt;/system_observation&gt;")
    sanitized = sanitized.replace("<system_observation", "&lt;system_observation")
    return sanitized


def format_system_observation(context: SystemContext) -> str:
    """Format SystemContext into an encapsulated, untrusted observation block per D-03 and CTXT-03."""
    lines = [
        f"OS Distribution: {context.os_name} (family: {context.os_family}, version: {context.os_version})",
        f"Kernel & Architecture: {context.kernel} {context.arch}",
        f"User & Privileges: {context.user} (is_root: {context.is_root})",
        f"Working Directory: {context.cwd}",
        f"Active Shell: {context.shell}",
        f"Primary Package Manager: {context.package_manager}",
    ]

    if context.git_branch:
        clean_status = "clean" if context.git_clean else "dirty (uncommitted changes)"
        lines.append(f"Git Repository: branch '{context.git_branch}', status: {clean_status}")
    else:
        lines.append("Git Repository: not a git repository")

    if context.env_vars:
        env_lines = [f"  {k}={v}" for k, v in sorted(context.env_vars.items())]
        lines.append("Environment Variables (Allowlisted):")
        lines.extend(env_lines)

    raw_body = "\n".join(lines)
    safe_body = sanitize_boundary_text(raw_body)

    return f'<system_observation untrusted="true">\n{safe_body}\n</system_observation>'
