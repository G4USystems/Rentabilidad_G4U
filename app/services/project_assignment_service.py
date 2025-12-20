"""Service for suggesting project assignments based on transaction text."""

from __future__ import annotations

from typing import List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.transaction import Transaction


class ProjectAssignmentService:
    """Suggest project assignments using project metadata and keywords."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._projects_cache: Optional[List[Project]] = None

    async def get_active_projects(self) -> List[Project]:
        """Fetch active projects with caching."""
        if self._projects_cache is None:
            result = await self.db.execute(
                select(Project).where(Project.is_active == True)
            )
            self._projects_cache = list(result.scalars().all())
        return self._projects_cache

    def clear_cache(self) -> None:
        """Clear cached projects."""
        self._projects_cache = None

    def _score_match(
        self,
        match_text: str,
        term: Optional[str],
        weight: int,
        matched_terms: Set[str],
    ) -> int:
        if not term:
            return 0
        cleaned = term.strip().lower()
        if not cleaned:
            return 0
        if cleaned in match_text:
            matched_terms.add(cleaned)
            return weight * len(cleaned)
        return 0

    def _project_score(self, project: Project, match_text: str) -> Tuple[int, List[str]]:
        matched_terms: Set[str] = set()
        score = 0

        score += self._score_match(match_text, project.code, 3, matched_terms)
        score += self._score_match(match_text, project.name, 2, matched_terms)
        score += self._score_match(match_text, project.client_name, 3, matched_terms)

        for tag in project.tag_list:
            score += self._score_match(match_text, tag, 1, matched_terms)

        return score, sorted(matched_terms)

    async def suggest_project_for_transaction(
        self,
        transaction: Transaction,
        min_score: int = 3,
    ) -> Optional[dict]:
        """
        Suggest a project for a transaction.

        Returns a dict with suggestion details or None if no match.
        """
        match_text = " ".join(
            part
            for part in [
                transaction.label,
                transaction.counterparty_name or "",
                transaction.note or "",
                transaction.reference or "",
            ]
            if part
        ).lower()

        if not match_text:
            return None

        projects = await self.get_active_projects()
        best_score = 0
        best_project: Optional[Project] = None
        best_terms: List[str] = []

        for project in projects:
            score, matched_terms = self._project_score(project, match_text)
            if score > best_score:
                best_score = score
                best_project = project
                best_terms = matched_terms
            elif score == best_score and score > 0 and best_project:
                if len(matched_terms) > len(best_terms):
                    best_project = project
                    best_terms = matched_terms

        if not best_project or best_score < min_score:
            return None

        return {
            "project_id": best_project.id,
            "project_name": best_project.name,
            "project_code": best_project.code,
            "client_name": best_project.client_name,
            "score": best_score,
            "matched_terms": best_terms,
        }
