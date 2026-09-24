from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.application.dto import ChatRequest, ChatResponse
from fastapi import APIRouter
from app.application import chat as service

from app.domain.application_error import ApplicationError

router = APIRouter()


@router.post('/projects/{project_id}/chat', response_model=ChatResponse)
def chat(project_id: str, payload: ChatRequest, db: Session = Depends(get_db)):
    return service.chat(project_id, payload, db)


@router.post('/projects/{project_id}/chat/proposals/{proposal_id}/confirm', status_code=410)
@router.post('/projects/{project_id}/chat/proposals/{proposal_id}/cancel', status_code=410)
def retired_chat_edit(project_id: str, proposal_id: str):
    raise ApplicationError(410, '채팅 정책 수정 기능이 종료되었습니다. 관련 소스를 업데이트해 주세요.')
