# -*- coding: utf-8 -*-
"""
core.py
=======
`Jarvis` class ka composition root.

Ye class koi naya behaviour add nahi karti — bas focused mixins ko ek saath
jodti hai. MRO me lifecycle pehle hai (constructor + run_forever yahan se
aate hain), baaki sab sirf uske helpers use karte hain.

Mixins alag files me hain taaki ek feature badalna ho toh poora class na
padhna pade:

    LifecycleMixin      __init__, run_forever, shutdown, wake, speak, listen
    IntentRouterMixin   handle_text (intent pipeline)
    FeatureRoutesMixin  keyword route handlers
    CommandDispatchMixin matched command types + param extraction
    FeatureActionsMixin memory + email
    InfoActionsMixin    no-argument actions
    AiActionsMixin      streaming AI + AI function-calling
    VisionActionsMixin  screen / code / file intake
    SystemActionsMixin  app launch + keyboard
    ChatActionsMixin    chat mode
    MediaActionsMixin   video notes

Split karne se pehle `handle_text()` ke andar 9 pending-prompt blocks aur 12
keyword blocks inline the; ab wo `followups.RULES` aur `keyword_routes.*` me
data-driven hain, isliye naye features add karna = table me ek row daalna.
"""

from .ai_actions import AiActionsMixin
from .chat_actions import ChatActionsMixin
from .command_dispatch import CommandDispatchMixin
from .feature_actions import FeatureActionsMixin
from .feature_routes import FeatureRoutesMixin
from .info_actions import InfoActionsMixin
from .lifecycle import LifecycleMixin
from .media_actions import MediaActionsMixin
from .router import IntentRouterMixin
from .system_actions import SystemActionsMixin
from .vision_actions import VisionActionsMixin


class JarvisCore(
    LifecycleMixin,
    IntentRouterMixin,
    FeatureRoutesMixin,
    CommandDispatchMixin,
    FeatureActionsMixin,
    InfoActionsMixin,
    AiActionsMixin,
    VisionActionsMixin,
    SystemActionsMixin,
    ChatActionsMixin,
    MediaActionsMixin,
):
    """Saari Jarvis behaviour — focused mixins se composed."""