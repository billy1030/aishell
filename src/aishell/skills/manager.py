"""Skill discovery, YAML frontmatter parsing, and dynamic prompt injection."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from aishell.config.settings import get_default_config_dir
from aishell.skills.builtins import BUILTIN_SKILLS
from aishell.skills.schema import Skill

_FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n(.*)$", re.DOTALL)


def _parse_frontmatter(raw_text: str, fallback_name: str, source: str) -> Skill:
    """Parse a SKILL.md file with optional YAML frontmatter into a Skill model."""
    name = fallback_name
    description = ""
    triggers: List[str] = []
    body = raw_text.strip()

    match = _FRONTMATTER_RE.match(raw_text)
    if match:
        fm_block, body_block = match.group(1), match.group(2)
        body = body_block.strip()
        for line in fm_block.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" in stripped:
                k, v = stripped.split(":", 1)
                key = k.strip().lower()
                val = v.strip().strip('"').strip("'")
                if key == "name" and val:
                    name = val
                elif key == "description":
                    description = val
                elif key == "triggers":
                    # Support comma-separated or [a, b, c] list syntax
                    cleaned = val.strip("[]")
                    triggers = [
                        t.strip().strip('"').strip("'")
                        for t in cleaned.split(",")
                        if t.strip()
                    ]

    if not description:
        for line in body.splitlines():
            clean_line = line.strip().lstrip("#").strip()
            if clean_line:
                description = clean_line[:120]
                break

    if not triggers:
        triggers = [name.lower(), name.replace("-", " ").lower()]

    return Skill(
        name=name,
        description=description,
        instructions=body,
        triggers=triggers,
        source=source,
    )


class SkillManager:
    """Loads hierarchical AI skills (project > user > builtin) and matches them to queries."""

    def __init__(
        self,
        user_skills_dir: Optional[Path] = None,
        project_dir: Optional[Path] = None,
    ) -> None:
        self.user_skills_dir = user_skills_dir or (get_default_config_dir() / "skills")
        self.project_dir = project_dir or Path.cwd()
        self._skills: Dict[str, Skill] = {}
        self.reload()

    def reload(self) -> None:
        """Discover and load skills in precedence order: builtin < user < project."""
        loaded: Dict[str, Skill] = {}

        # 1. Built-in skills
        for s in BUILTIN_SKILLS:
            loaded[s.name.lower()] = s

        # 2. User skills (~/.config/aishell/skills/)
        self._scan_directory(self.user_skills_dir, source="user", target=loaded)

        # 3. Project/workspace skills (.aishell/skills/ or .agents/skills/)
        self._scan_directory(self.project_dir / ".aishell" / "skills", source="project", target=loaded)
        self._scan_directory(self.project_dir / ".agents" / "skills", source="project", target=loaded)

        self._skills = loaded

    def _scan_directory(self, directory: Path, source: str, target: Dict[str, Skill]) -> None:
        """Scan a directory for <skill>/SKILL.md or <skill>.md files."""
        if not directory.exists() or not directory.is_dir():
            return

        for entry in sorted(directory.iterdir()):
            try:
                if entry.is_dir():
                    skill_file = entry / "SKILL.md"
                    if skill_file.is_file():
                        skill = _parse_frontmatter(
                            skill_file.read_text(encoding="utf-8"),
                            fallback_name=entry.name,
                            source=source,
                        )
                        target[skill.name.lower()] = skill
                elif entry.is_file() and entry.suffix.lower() == ".md":
                    skill = _parse_frontmatter(
                        entry.read_text(encoding="utf-8"),
                        fallback_name=entry.stem,
                        source=source,
                    )
                    target[skill.name.lower()] = skill
            except Exception:
                continue

    def list_skills(self) -> List[Skill]:
        """Return all available skills sorted by name."""
        return sorted(self._skills.values(), key=lambda s: s.name.lower())

    def get_skill(self, name: str) -> Optional[Skill]:
        """Retrieve a skill by exact name (case-insensitive)."""
        return self._skills.get(name.strip().lower())

    def match_skills(self, query: str, max_skills: int = 2) -> List[Skill]:
        """Match skills explicitly (@skill / /skill) or via trigger keywords."""
        q_lower = query.lower()
        matched: List[Skill] = []
        seen = set()

        # 1. Explicit @skill_name or /skill_name mentions
        for token in re.findall(r"[@/]([a-zA-Z0-9_-]+)", query):
            skill = self.get_skill(token)
            if skill and skill.name not in seen:
                matched.append(skill)
                seen.add(skill.name)

        # 2. Automatic trigger keyword matching
        for skill in self._skills.values():
            if skill.name in seen:
                continue
            for trig in skill.triggers:
                if trig and trig.lower() in q_lower:
                    matched.append(skill)
                    seen.add(skill.name)
                    break
            if len(matched) >= max_skills:
                break

        return matched[:max_skills]

    def format_skills_context(self, skills: List[Skill]) -> str:
        """Format active skill instructions into XML blocks for system prompt injection."""
        if not skills:
            return ""
        blocks = []
        for s in skills:
            blocks.append(
                f'<active_skill name="{s.name}" source="{s.source}">\n'
                f"{s.instructions}\n"
                "</active_skill>"
            )
        return "\n\n".join(blocks)

    @property
    def _approvals_path(self) -> Path:
        return self.user_skills_dir.parent / "approved_skills.json"

    DEFAULT_PREAPPROVED_SKILLS: Set[str] = {"web-search", "web-fetch"}

    def load_approved_skills(self) -> Set[str]:
        """Load permanently auto-approved skill names from disk, including pre-approved defaults."""
        approved = set(self.DEFAULT_PREAPPROVED_SKILLS)
        try:
            if self._approvals_path.is_file():
                data = json.loads(self._approvals_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    approved.update(str(x).strip().lower() for x in data if str(x).strip())
        except Exception:
            pass
        return approved

    def save_approved_skill(self, skill_name: str) -> None:
        """Persist a skill name as permanently auto-approved."""
        approved = self.load_approved_skills()
        approved.add(skill_name.strip().lower())
        try:
            self._approvals_path.parent.mkdir(parents=True, exist_ok=True)
            self._approvals_path.write_text(
                json.dumps(sorted(approved), indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

