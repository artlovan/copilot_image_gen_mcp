"""
config.py — Centralized configuration for the image generation MCP server.

All configuration lives here. Values come from sensible defaults with
environment variable overrides. No module should hardcode endpoints,
feature flags, or paths.
"""

from __future__ import annotations

import os
from pathlib import Path


# ── WebSocket Endpoint ──────────────────────────────────────────────────────

WS_HOST = os.environ.get(
    "COPILOT_WS_HOST",
    "substrate.svc.cloud.microsoft",
)

WS_PATH_TEMPLATE = "/m365Copilot/Chathub/{oid}@{tid}"

REQUIRED_ORIGIN = "https://m365.cloud.microsoft"


# ── Authentication ──────────────────────────────────────────────────────────

CLIENT_ID = "c0ab8ce9-e9a0-42e7-b064-33d422df41f1"
SYDNEY_RESOURCE = "https://substrate.office.com/sydney"
SCOPES = f"{SYDNEY_RESOURCE}/.default openid profile offline_access"
REDIRECT_URI = "https://login.microsoftonline.com/common/oauth2/nativeclient"
TENANT = os.environ.get("COPILOT_TENANT", "common")

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token"
AUTHORIZE_URL = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/authorize"


# ── Image Storage ───────────────────────────────────────────────────────────

def get_images_dir() -> Path:
    """Base directory for saved images. Cross-platform."""
    env_override = os.environ.get("COPILOT_IMAGES_DIR")
    if env_override:
        return Path(env_override)
    return Path.home() / ".copilot-images"


def get_cache_dir() -> Path:
    """Token cache directory. Cross-platform."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", str(Path.home()))
        return Path(base) / "copilot-image-gen-mcp"
    return Path.home() / ".copilot-image-gen-mcp"


# ── Browser ─────────────────────────────────────────────────────────────────

DEFAULT_BROWSER = os.environ.get("COPILOT_BROWSER", "msedge")


# ── Variants (Feature Flags) ───────────────────────────────────────────────
# These are required for image generation to work. Without them the server
# returns "OperationNotSupported - completion operation does not work with
# specified model". They may evolve over time — override via COPILOT_VARIANTS.

_DEFAULT_VARIANTS = (
    "EnableMcpServerWidgets,feature.EnableMcpServerWidgets,"
    "feature.EnableLuForChatCIQ,feature.enableChatCIQPlugin,"
    "EnableRequestPlugins,feature.EnableSensitivityLabels,"
    "EnableUnsupportedUrlDetector,MetricsSummaryEnabled,"
    "feature.EnableMessageExtensionAnnotations,"
    "3S.ProcessMECardTitleForEntityAnotation,"
    "feature.IsCustomEngineCopilotEnabled,feature.bizchatfluxv3,"
    "feature.IsOpenApiAnnotationsEnabled,feature.EnableConnectorAnnotations,"
    "feature.enablechatpages,feature.enableCodeCanvasWork,"
    "feature.turnOnWorkTabRecommendation,turnOffWorkTabUpsellFromClient,"
    "feature.turnOnDARecommendation,"
    "feature.IsStreamingModeInChatRequestEnabled,"
    "IncludeSourceAttributionsConcise,SkipPublishEmptyMessage,"
    "feature.EnableDeduplicatingSourceAttributions,"
    "feature.IsCitationsReferencesOutputEnabled,"
    "feature.enableDeltaStreamingForReferences,"
    "feature.enableIncludeReferencesInDeltaResponse,"
    "feature.enablereferencesforagents,"
    "Enable3PActionProgressMessages,"
    "feature.EnableCIQDesktopDisplay,feature.enableClientWebRtc,"
    "feature.EnableMeetingRecapOfSeriesMeetingWithCiq,"
    "feature.EnableReferencesListCompleteSignal,"
    "feature.StorageMessageSplitDisabled,feature.EnableCuaTakeControlApi,"
    "cdxdeepciteline,EnableDeepCitationsMetadataInSearchResponse,"
    "feature.isExternalEmailEnabled,feature.isExcludedEmailEnabled,"
    "feature.disabledisallowedmsgs,feature.enableCitationsForSynthesisData,"
    "feature.EnableConversationShareApis,"
    "feature.enableGenerateGraphicArtOptionsSet,cdximagen,"
    "feature.bizChatAugLoopCalendarAgent,feature.EnableCuaTakeControlApi,"
    "feature.EnableUpdatedUXForConfirmationDialog,"
    "feature.EnableContentApiandDocTypeHtmlInRichAnswers,"
    "cdxgrounding_api_v2_rich_web_answers_reference_bottom_force,"
    "cdxenablerenderforisocomp,feature.EnableDesignEditorImageGrounding,"
    "feature.EnableDesignerEditor,"
    "feature.EnableSkipRehydrationForSpeCIdImages,"
    "feature.EnablePersonalization,cdxentrecapvifluxv3,"
    "agt_bizchat_enableRichResponses,"
    "feature.EnableBase64DataInMessageAnnotations,"
    "feature.EnableSkipEmittingMessageOnFlush,"
    "feature.EnableRemoveEmptySourceAttributions,"
    "feature.EnableRemoveStreamingMode,"
    "feature.OfficeWebToHelix,feature.OfficeDesktopToHelix,"
    "feature.M365TeamsHubToHelix,feature.OwaHubToHelix,"
    "feature.MonarchHubToHelix,feature.Win32OutlookHubToHelix,"
    "feature.MacOutlookHubToHelix,Agt_bizchat_enableGpt5ForHelix"
)

VARIANTS = os.environ.get("COPILOT_VARIANTS", _DEFAULT_VARIANTS)


# ── Options Sets ────────────────────────────────────────────────────────────
# Sent in the chat message to enable image generation capabilities.

IMAGE_GEN_OPTIONS_SETS = [
    "enterprise_flux_image",
    "flux_v3_image_gen_enable_dimensions",
    "flux_v3_image_gen_enable_icon_dimensions",
    "flux_v3_image_gen_enable_system_text_with_params",
    "flux_v3_image_gen_enable_designer_dimensions_meta_prompting_in_system_prompts",
]

BASE_OPTIONS_SETS = [
    "at_mention_plugins_enable",
    "enable_confirmation_interstitial",
    "enable_plugin_auth_interstitial",
    "enable_request_response_interstitials",
    "enable_response_action_processing",
    "enterprise_flux_web",
    "enterprise_flux_work",
    "enterprise_toolbox_with_skdsstore",
    "enterprise_pagination_support",
    "search_result_progress_messages_with_search_queries",
    "flux_v3_gptv_enable_upload_multi_image_in_turn_wo_ch",
    "rich_responses",
    "gptvnorm2048",
    "enterprise_flux_work_code_interpreter",
    "cwc_code_interpreter_citation_fix",
    "code_interpreter_interactive_charts",
    "enterprise_code_interpreter_citation_fix",
    "cwc_code_interpreter_interactive_charts_inline_image",
    "code_interpreter_matplotlib_patching",
    "enable_batch_token_processing",
    "disable_cea_message_listener",
    "enable_selective_url_redaction",
    "update_memory_plugin",
    "add_custom_instructions",
    "agent_recommendations",
    "enable_gg_gpt",
    "enable_inferred_memory_read",
    "enable_deep_citations_lines",
    "flux_v3_references",
    "flux_v3_references_entities",
]


# ── Allowed Message Types ───────────────────────────────────────────────────

ALLOWED_MESSAGE_TYPES = [
    "ActionRequest",
    "Chat",
    "ConfirmationCard",
    "Context",
    "Disengaged",
    "InternalSearchQuery",
    "InternalSearchResult",
    "InternalLoaderMessage",
    "Progress",
    "RenderCardRequest",
    "RenderContentRequest",
    "AdsQuery",
    "SemanticSerp",
    "GenerateContentQuery",
    "GeneratedCode",
    "SearchQuery",
    "Suggestion",
    "Disclaimer",
]


# ── URL Parameters ──────────────────────────────────────────────────────────

def get_ws_url_params(
    access_token: str,
    conversation_id: str = "",
    session_id: str = "",
    request_id: str = "",
) -> dict[str, str]:
    """Build the URL query parameters for the WebSocket connection."""
    params = {
        "access_token": access_token,
        "source": "officeweb",
        "product": "Office",
        "agentHost": "Bizchat.FullScreen",
        "licenseType": "Premium",
        "agent": "work",
        "scenario": "officeweb",
        "variants": VARIANTS,
    }
    if conversation_id:
        params["ConversationId"] = conversation_id
    if session_id:
        params["X-SessionId"] = session_id
    if request_id:
        params["chatsessionid"] = request_id
        params["clientrequestid"] = request_id
        params["XRoutingParameterSessionKey"] = request_id
    return params


# ── Client Info ─────────────────────────────────────────────────────────────

CLIENT_INFO = {
    "clientPlatform": "mcmcopilot-web",
    "clientAppName": "Office",
    "clientEntrypoint": "mcmcopilot-officeweb",
    "clientAppType": "Web",
    "deviceOS": "macOS",
    "deviceType": "Desktop",
}


# ── Timeouts ────────────────────────────────────────────────────────────────

WS_CONNECT_TIMEOUT_SECONDS = 15
IMAGE_GEN_TIMEOUT_SECONDS = int(os.environ.get("COPILOT_TIMEOUT", "90"))
WS_PING_INTERVAL_SECONDS = 15
