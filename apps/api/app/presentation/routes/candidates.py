from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.domain import CandidateDecision
from app.application.dto import CandidateDetail, CandidateOut, CandidateReview, PolicyOut
from fastapi import APIRouter
from app.application import candidates as service

router = APIRouter()


@router.get('/projects/{project_id}/policy-candidates', response_model=list[CandidateOut])
def list_candidates(project_id: str, decision: CandidateDecision = CandidateDecision.PENDING, db: Session = Depends(get_db)):
    return service.list_candidates(project_id, decision, db)


@router.get('/policy-candidates/{candidate_id}', response_model=CandidateDetail)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)):
    return service.get_candidate(candidate_id, db)


@router.post('/policy-candidates/{candidate_id}/approve', response_model=PolicyOut)
def approve_candidate(candidate_id: str, payload: CandidateReview, db: Session = Depends(get_db)):
    return service.approve_candidate(candidate_id, payload, db)


@router.post('/policy-candidates/{candidate_id}/merge', response_model=PolicyOut)
def merge_candidate(candidate_id: str, payload: CandidateReview, db: Session = Depends(get_db)):
    return service.merge_candidate(candidate_id, payload, db)


@router.post('/policy-candidates/{candidate_id}/reject', status_code=204)
def reject_candidate(candidate_id: str, db: Session = Depends(get_db)):
    return service.reject_candidate(candidate_id, db)
