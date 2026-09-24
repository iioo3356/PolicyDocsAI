from sqlalchemy import select
from sqlalchemy.orm import Session
from app.application.dto.chat_response import ChatResponse
from app.application.dto.chat_source_suggestion import ChatSourceSuggestion
from app.infrastructure.models import Policy, Source, SourceChunk, SourceFile
from .chat_context import latest_revision, citations_for


def source_guidance(db: Session, policies: list[Policy]) -> ChatResponse:
    suggestions = []
    seen = set()
    for policy in policies:
        revision = latest_revision(db, policy.id)
        source_id = revision.after.get('_source', {}).get('source_id') if revision else None
        if source_id:
            sources = [db.get(Source, source_id)]
        else:
            chunk_ids = [e.source_chunk_id for e in policy.evidence]
            sources = db.scalars(select(Source).join(SourceFile, SourceFile.source_id == Source.id)
                                 .join(SourceChunk, SourceChunk.source_file_id == SourceFile.id)
                                 .where(SourceChunk.id.in_(chunk_ids))).all()
        for source in sources:
            if source and (source.id, policy.id) not in seen:
                seen.add((source.id, policy.id))
                suggestions.append(ChatSourceSuggestion(source_id=source.id, source_name=source.name,
                                                        policy_id=policy.id, policy_title=policy.title))
    return ChatResponse(action='update_source', answer='정책은 소스를 기준으로 관리합니다. '
                        '관련 소스를 수정해 다시 업로드한 뒤, 정책 관리에서 변경 후보를 검토·승인해 주세요. '
                        '승인하면 정책과 수정 이력이 함께 갱신됩니다. 채팅에서는 정책을 변경하지 않습니다.',
                        grounded=bool(policies), related_policies=policies, citations=citations_for(db, policies),
                        source_suggestions=suggestions)
