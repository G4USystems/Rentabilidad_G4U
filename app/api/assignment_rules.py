"""API endpoints for assignment rules."""

from typing import Optional, List
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from pydantic import BaseModel

from app.core.database import get_db
from app.models.assignment_rule import AssignmentRule
from app.models.project import Project
from app.models.transaction import Transaction
from app.schemas.assignment_rule import (
    AssignmentRuleCreate,
    AssignmentRuleUpdate,
    AssignmentRuleResponse,
    AssignmentRuleListResponse,
    RuleSuggestion,
    TransactionRuleSuggestion,
)

router = APIRouter()


@router.get("", response_model=AssignmentRuleListResponse)
async def list_rules(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List all assignment rules."""
    query = (
        select(AssignmentRule)
        .options(joinedload(AssignmentRule.project))
        .order_by(AssignmentRule.priority.desc(), AssignmentRule.name)
    )

    if active_only:
        query = query.where(AssignmentRule.is_active == True)

    result = await db.execute(query)
    rules = result.unique().scalars().all()

    items = [
        AssignmentRuleResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            keywords=r.keywords,
            counterparty=r.counterparty,
            counterparty_pattern=r.counterparty_pattern,
            client_name_suggested=r.client_name_suggested,
            project_id_suggested=r.project_id_suggested,
            project_name=r.project.name if r.project else None,
            project_code=r.project.code if r.project else None,
            priority=r.priority,
            is_active=r.is_active,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rules
    ]

    return AssignmentRuleListResponse(items=items, total=len(items))


@router.post("", response_model=AssignmentRuleResponse)
async def create_rule(
    rule: AssignmentRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new assignment rule."""
    # Validate project if provided
    if rule.project_id_suggested:
        result = await db.execute(
            select(Project).where(Project.id == rule.project_id_suggested)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    else:
        project = None

    # Create rule
    db_rule = AssignmentRule(
        name=rule.name,
        description=rule.description,
        keywords=rule.keywords,
        counterparty=rule.counterparty,
        counterparty_pattern=rule.counterparty_pattern,
        client_name_suggested=rule.client_name_suggested,
        project_id_suggested=rule.project_id_suggested,
        priority=rule.priority,
        is_active=rule.is_active,
    )
    db.add(db_rule)
    await db.flush()
    await db.refresh(db_rule)

    return AssignmentRuleResponse(
        id=db_rule.id,
        name=db_rule.name,
        description=db_rule.description,
        keywords=db_rule.keywords,
        counterparty=db_rule.counterparty,
        counterparty_pattern=db_rule.counterparty_pattern,
        client_name_suggested=db_rule.client_name_suggested,
        project_id_suggested=db_rule.project_id_suggested,
        project_name=project.name if project else None,
        project_code=project.code if project else None,
        priority=db_rule.priority,
        is_active=db_rule.is_active,
        created_at=db_rule.created_at,
        updated_at=db_rule.updated_at,
    )


@router.get("/{rule_id}", response_model=AssignmentRuleResponse)
async def get_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single assignment rule."""
    result = await db.execute(
        select(AssignmentRule)
        .options(joinedload(AssignmentRule.project))
        .where(AssignmentRule.id == rule_id)
    )
    rule = result.unique().scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return AssignmentRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        keywords=rule.keywords,
        counterparty=rule.counterparty,
        counterparty_pattern=rule.counterparty_pattern,
        client_name_suggested=rule.client_name_suggested,
        project_id_suggested=rule.project_id_suggested,
        project_name=rule.project.name if rule.project else None,
        project_code=rule.project.code if rule.project else None,
        priority=rule.priority,
        is_active=rule.is_active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.patch("/{rule_id}", response_model=AssignmentRuleResponse)
async def update_rule(
    rule_id: int,
    update: AssignmentRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an assignment rule."""
    result = await db.execute(
        select(AssignmentRule).where(AssignmentRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Validate project if being updated
    update_data = update.model_dump(exclude_unset=True)
    if "project_id_suggested" in update_data and update_data["project_id_suggested"]:
        result = await db.execute(
            select(Project).where(Project.id == update_data["project_id_suggested"])
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Project not found")

    # Update fields
    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.flush()
    await db.refresh(rule)

    # Reload with project
    result = await db.execute(
        select(AssignmentRule)
        .options(joinedload(AssignmentRule.project))
        .where(AssignmentRule.id == rule_id)
    )
    rule = result.unique().scalar_one()

    return AssignmentRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        keywords=rule.keywords,
        counterparty=rule.counterparty,
        counterparty_pattern=rule.counterparty_pattern,
        client_name_suggested=rule.client_name_suggested,
        project_id_suggested=rule.project_id_suggested,
        project_name=rule.project.name if rule.project else None,
        project_code=rule.project.code if rule.project else None,
        priority=rule.priority,
        is_active=rule.is_active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an assignment rule."""
    result = await db.execute(
        select(AssignmentRule).where(AssignmentRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(rule)
    await db.flush()

    return {"status": "success", "deleted_id": rule_id}


@router.get("/suggest/{transaction_id}", response_model=TransactionRuleSuggestion)
async def suggest_for_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get rule-based suggestions for a transaction.

    Evaluates all active rules against the transaction and returns
    matching suggestions ordered by priority.
    """
    # Get transaction
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Get all active rules ordered by priority
    result = await db.execute(
        select(AssignmentRule)
        .options(joinedload(AssignmentRule.project))
        .where(AssignmentRule.is_active == True)
        .order_by(AssignmentRule.priority.desc())
    )
    rules = result.unique().scalars().all()

    # Find matching rules
    suggestions = []
    for rule in rules:
        if rule.matches_transaction(tx.label, tx.counterparty_name):
            # Build reason string
            reasons = []
            if rule.keywords and any(k in tx.label.lower() for k in rule.keyword_list):
                matched_keywords = [k for k in rule.keyword_list if k in tx.label.lower()]
                reasons.append(f"keyword match: {', '.join(matched_keywords)}")
            if rule.counterparty and tx.counterparty_name and \
               rule.counterparty.lower() == tx.counterparty_name.lower():
                reasons.append(f"counterparty match: {rule.counterparty}")
            if rule.counterparty_pattern:
                reasons.append(f"counterparty pattern: {rule.counterparty_pattern}")

            suggestions.append(
                RuleSuggestion(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    project_id=rule.project_id_suggested,
                    project_name=rule.project.name if rule.project else None,
                    project_code=rule.project.code if rule.project else None,
                    client_name=rule.client_name_suggested,
                    reason=" | ".join(reasons) if reasons else "Rule match",
                    priority=rule.priority,
                )
            )

    return TransactionRuleSuggestion(
        transaction_id=transaction_id,
        suggestions=suggestions,
    )


@router.post("/suggest/bulk", response_model=List[TransactionRuleSuggestion])
async def bulk_suggest_for_transactions(
    transaction_ids: List[int],
    db: AsyncSession = Depends(get_db),
):
    """Get rule-based suggestions for multiple transactions."""
    # Get transactions
    result = await db.execute(
        select(Transaction).where(Transaction.id.in_(transaction_ids))
    )
    transactions = result.scalars().all()

    # Get all active rules
    result = await db.execute(
        select(AssignmentRule)
        .options(joinedload(AssignmentRule.project))
        .where(AssignmentRule.is_active == True)
        .order_by(AssignmentRule.priority.desc())
    )
    rules = result.unique().scalars().all()

    # Process each transaction
    results = []
    for tx in transactions:
        suggestions = []
        for rule in rules:
            if rule.matches_transaction(tx.label, tx.counterparty_name):
                reasons = []
                if rule.keywords and any(k in tx.label.lower() for k in rule.keyword_list):
                    matched_keywords = [k for k in rule.keyword_list if k in tx.label.lower()]
                    reasons.append(f"keyword match: {', '.join(matched_keywords)}")
                if rule.counterparty and tx.counterparty_name and \
                   rule.counterparty.lower() == tx.counterparty_name.lower():
                    reasons.append(f"counterparty match: {rule.counterparty}")
                if rule.counterparty_pattern:
                    reasons.append(f"counterparty pattern: {rule.counterparty_pattern}")

                suggestions.append(
                    RuleSuggestion(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        project_id=rule.project_id_suggested,
                        project_name=rule.project.name if rule.project else None,
                        project_code=rule.project.code if rule.project else None,
                        client_name=rule.client_name_suggested,
                        reason=" | ".join(reasons) if reasons else "Rule match",
                        priority=rule.priority,
                    )
                )

        results.append(
            TransactionRuleSuggestion(
                transaction_id=tx.id,
                suggestions=suggestions,
            )
        )

    return results


class BatchImportResult(BaseModel):
    """Result of batch import."""
    total_rows: int
    imported: int
    skipped: int
    errors: List[dict]


@router.post("/import/csv", response_model=BatchImportResult)
async def import_rules_from_csv(
    file: UploadFile = File(...),
    skip_duplicates: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Import assignment rules from a CSV file.

    CSV format:
    name,keywords,counterparty,counterparty_pattern,client_name_suggested,project_code,priority

    Example:
    AWS Services,aws amazon ec2,,aws.*,TechCorp,PROJ-001,100
    Google Ads,google ads advertising,Google Ireland,,Marketing Client,,90
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(text))

    result = BatchImportResult(
        total_rows=0,
        imported=0,
        skipped=0,
        errors=[],
    )

    # Get projects for lookup by code
    project_result = await db.execute(select(Project))
    projects = {p.code: p for p in project_result.scalars().all() if p.code}

    for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        result.total_rows += 1

        try:
            name = row.get('name', '').strip()
            if not name:
                result.errors.append({
                    "row": row_num,
                    "error": "Name is required",
                    "data": row,
                })
                continue

            # Check for duplicate
            if skip_duplicates:
                existing = await db.execute(
                    select(AssignmentRule).where(AssignmentRule.name == name)
                )
                if existing.scalar_one_or_none():
                    result.skipped += 1
                    continue

            # Lookup project by code
            project_id = None
            project_code = row.get('project_code', '').strip()
            if project_code and project_code in projects:
                project_id = projects[project_code].id

            # Parse priority
            priority = 0
            if row.get('priority'):
                try:
                    priority = int(row['priority'])
                except ValueError:
                    pass

            # Create rule
            rule = AssignmentRule(
                name=name,
                keywords=row.get('keywords', '').strip() or None,
                counterparty=row.get('counterparty', '').strip() or None,
                counterparty_pattern=row.get('counterparty_pattern', '').strip() or None,
                client_name_suggested=row.get('client_name_suggested', '').strip() or None,
                project_id_suggested=project_id,
                priority=priority,
                is_active=True,
            )
            db.add(rule)
            result.imported += 1

        except Exception as e:
            result.errors.append({
                "row": row_num,
                "error": str(e),
                "data": row,
            })

    await db.commit()
    return result


@router.get("/export/csv")
async def export_rules_to_csv(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Export all assignment rules to CSV format."""
    from fastapi.responses import StreamingResponse

    query = (
        select(AssignmentRule)
        .options(joinedload(AssignmentRule.project))
        .order_by(AssignmentRule.priority.desc())
    )

    if active_only:
        query = query.where(AssignmentRule.is_active == True)

    result = await db.execute(query)
    rules = result.unique().scalars().all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'name', 'keywords', 'counterparty', 'counterparty_pattern',
        'client_name_suggested', 'project_code', 'priority', 'is_active'
    ])

    # Data
    for rule in rules:
        writer.writerow([
            rule.name,
            rule.keywords or '',
            rule.counterparty or '',
            rule.counterparty_pattern or '',
            rule.client_name_suggested or '',
            rule.project.code if rule.project else '',
            rule.priority,
            rule.is_active,
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=assignment_rules.csv"},
    )
