"""Phase handlers package.

Each phase has its own handler that:
1. Loads prompt configuration from ~/.bmad-assist/handlers/{phase}.yaml
2. Renders the prompt template with state context
3. Invokes the configured provider
4. Returns PhaseResult with provider output

"""

from bmad_assist.core.loop.handlers.base import BaseHandler, HandlerConfig
from bmad_assist.core.loop.handlers.code_review import CodeReviewHandler
from bmad_assist.core.loop.handlers.code_review_synthesis import CodeReviewSynthesisHandler
from bmad_assist.core.loop.handlers.create_story import CreateStoryHandler
from bmad_assist.core.loop.handlers.dev_story import DevStoryHandler
from bmad_assist.core.loop.handlers.qa_plan_execute import QaPlanExecuteHandler
from bmad_assist.core.loop.handlers.qa_plan_generate import QaPlanGenerateHandler
from bmad_assist.core.loop.handlers.retrospective import RetrospectiveHandler
from bmad_assist.core.loop.handlers.validate_story import ValidateStoryHandler
from bmad_assist.core.loop.handlers.validate_story_synthesis import ValidateStorySynthesisHandler

__all__ = [
    "BaseHandler",
    "HandlerConfig",
    "CreateStoryHandler",
    "ValidateStoryHandler",
    "ValidateStorySynthesisHandler",
    "DevStoryHandler",
    "CodeReviewHandler",
    "CodeReviewSynthesisHandler",
    "RetrospectiveHandler",
    "QaPlanGenerateHandler",
    "QaPlanExecuteHandler",
]
