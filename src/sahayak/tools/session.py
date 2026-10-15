"""SessionManager: the only place identity and step-up state change.

Identity is set by the mock auth flow (`authenticate`) and step-up by the mock
OTP flow (`issue_otp` + `step_up`), both called by the channel or harness and
never by a tool. The condition is fixed at session creation. A session's
identity cannot be changed once set.
"""

from __future__ import annotations

import random
from dataclasses import replace

from sahayak.domain.models import Condition, Session
from sahayak.mockbank.repo import Repository

MAX_OTP_ATTEMPTS = 3


class SessionError(Exception):
    pass


class SessionManager:
    def __init__(self, repo: Repository, seed: int = 0):
        self._repo = repo
        self._rng = random.Random(seed)
        self._sessions: dict[str, Session] = {}
        self._otp: dict[str, str] = {}
        self._otp_attempts: dict[str, int] = {}

    def create(self, condition: Condition) -> Session:
        sid = f"S-{len(self._sessions) + 1:04d}"
        s = Session(sid, Condition(condition), None, False)
        self._sessions[sid] = s
        return s

    def get(self, session_id: str) -> Session:
        try:
            return self._sessions[session_id]
        except KeyError:
            raise SessionError(f"unknown session {session_id}") from None

    def authenticate(self, session_id: str, customer_id: str) -> Session:
        """Mock login. Identity can be set once and never changed."""
        s = self.get(session_id)
        if s.customer_id is not None:
            raise SessionError("session identity is already set and cannot change")
        if self._repo.get_customer(customer_id) is None:
            raise SessionError("unknown customer")
        s = replace(s, customer_id=customer_id)
        self._sessions[session_id] = s
        return s

    def issue_otp(self, session_id: str) -> str:
        """Mock OTP 'sent to the registered mobile'. Returned to the channel, never to the model."""
        s = self.get(session_id)
        if s.customer_id is None:
            raise SessionError("authenticate before step-up")
        code = f"{self._rng.randint(0, 999_999):06d}"
        self._otp[session_id] = code
        self._otp_attempts[session_id] = 0
        return code

    def step_up(self, session_id: str, code: str) -> bool:
        s = self.get(session_id)
        expected = self._otp.get(session_id)
        if expected is None or self._otp_attempts.get(session_id, 0) >= MAX_OTP_ATTEMPTS:
            return False
        self._otp_attempts[session_id] += 1
        if code != expected:
            return False
        del self._otp[session_id]
        self._sessions[session_id] = replace(s, step_up_verified=True)
        return True
