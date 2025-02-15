import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from ... import list_step_functions
from ...attr.step_functions import is_contrastive_step_function
from ...utils import cli_arg, pretty_dict
from ..attribute import AttributeBaseArgs
from ..commands_utils import command_args_docstring

logger = logging.getLogger(__name__)


class HandleOutputContextSetting(Enum):
    MANUAL = "manual"
    AUTO = "auto"
    PRE = "pre"


@command_args_docstring
@dataclass
class AttributeContextInputArgs:
    input_current_text: str = cli_arg(
        default="",
        help=(
            "The input text used for generation. If the model is a decoder-only model, the input text is a "
            "prompt used for language modeling. If the model is an encoder-decoder model, the input text is the "
            "source text provided as input to the encoder. It will be formatted as {current} in the "
            "``input_template``."
        ),
    )
    input_context_text: Optional[str] = cli_arg(
        default=None,
        help=(
            "Additional input context influencing the generation of ``output_current_text``. If the model is a"
            " decoder-only model, the input text is a prefix to the ``input_current_text`` prompt. If the model is an"
            " encoder-decoder model, the input context is part of the source text provided as input to the encoder. "
            " It will be formatted as {context} in the ``input_template``."
        ),
    )
    input_template: Optional[str] = cli_arg(
        default=None,
        help=(
            "The template used to format model inputs. The template must contain at least the"
            " ``{current}`` placeholder, which will be replaced by ``input_current_text``. If ``{context}`` is"
            " also specified, input-side context will be used. Can be modified for models requiring special tokens or"
            " formatting in the input text (e.g. <brk> tags to separate context and current inputs)."
            " Defaults to '{context} {current}' if ``input_context_text`` is provided, '{current}' otherwise."
        ),
    )
    output_context_text: Optional[str] = cli_arg(
        default=None,
        help=(
            "An output contexts for which context sensitivity should be detected. For encoder-decoder models, this"
            " is a target-side prefix to the output_current_text used as input to the decoder. For decoder-only "
            " models this is a portion of the model generation that should be considered as an additional context "
            " (e.g. a chain-of-thought sequence). It will be formatted as {context} in the ``output_template``."
            " If not provided but specified in the ``output_template``, the output context will be generated"
            " along with the output current text, and user validation might be required to separate the two."
        ),
    )
    output_current_text: Optional[str] = cli_arg(
        default=None,
        help=(
            "The output text generated by the model when all available contexts are provided. Tokens in "
            " ``output_current_text`` will be tested for context-sensitivity, and their generation will be attributed "
            " to input/target contexts (if present) in case they are found to be context-sensitive. If specified, "
            " this output is force-decoded. Otherwise, it is generated by the model using infilled ``input_template`` "
            " and ``output_template``. It will be formatted as {current} in the ``output_template``."
        ),
    )
    output_template: Optional[str] = cli_arg(
        default=None,
        help=(
            "The template used to format model outputs. The template must contain at least the"
            " ``{current}`` placeholder, which will be replaced by ``output_current_text``. If ``{context}`` is"
            " also specified, output-side context will be used. Can be modified for models requiring special tokens or"
            " formatting in the output text (e.g. <brk> tags to separate context and current outputs)."
            " Defaults to '{context} {current}' if ``output_context_text`` is provided, '{current}' otherwise."
        ),
    )
    contextless_input_current_text: Optional[str] = cli_arg(
        default=None,
        help=(
            "The input current text or template to use in the contrastive comparison with contextual input. By default"
            " it is the same as ``input_current_text``, but it can be useful in cases where the context is nested "
            "inside the current text (e.g. for an ``input_template`` like <user>\n{context}\n{current}\n<assistant> we "
            "can use this parameter to format the contextless version as <user>\n{current}\n<assistant>)."
            "If it contains the tag {current}, it will be infilled with the ``input_current_text``. Otherwise, it will"
            " be used as-is for the contrastive comparison, enabling contrastive comparison with different inputs."
        ),
    )


@command_args_docstring
@dataclass
class AttributeContextMethodArgs(AttributeBaseArgs):
    context_sensitivity_metric: str = cli_arg(
        default="kl_divergence",
        help="The contrastive metric used to detect context-sensitive tokens in ``output_current_text``.",
        choices=[fn for fn in list_step_functions() if is_contrastive_step_function(fn)],
    )
    handle_output_context_strategy: str = cli_arg(
        default=HandleOutputContextSetting.MANUAL.value,
        choices=[e.value for e in HandleOutputContextSetting],
        help=(
            "Specifies how output context should be handled when it is produced together with the output current text,"
            " and the two need to be separated for context sensitivity detection.\n"
            "Options:\n"
            "- `manual`: The user is prompted to verify an automatic context detection attempt, and optionally to"
            "  provide a correct context separation manually.\n"
            "- `auto`: Attempts an automatic detection of context using an automatic alignment with source context"
            " (assuming an MT-like task).\n"
            "- `pre`: If context is required but not pre-defined by the user via the ``output_context_text`` argument,"
            "  the execution will fail instead of attempting to prompt the user for the output context."
        ),
    )
    contextless_output_next_tokens: list[str] = cli_arg(
        default_factory=list,
        help=(
            "If specified, it should provide a list of one token per CCI output indicating the next token that should"
            " be force-decoded as contextless output instead of the natural output produced by"
            " ``get_contextless_output``. This is ignored if the ``attributed_fn`` used is not contrastive."
        ),
    )
    prompt_user_for_contextless_output_next_tokens: bool = cli_arg(
        default=False,
        help=(
            "If specified, the user is prompted to provide the next token that should be force-decoded as contextless"
            " output instead of the natural output produced by ``get_contextless_output``. This is ignored if the"
            " ``attributed_fn`` used is not contrastive."
        ),
    )
    special_tokens_to_keep: list[str] = cli_arg(
        default_factory=list,
        help="Special tokens to preserve in the generated string, e.g. ``<brk>`` separator between context and current.",
    )
    decoder_input_output_separator: str = cli_arg(
        default=" ",
        help=(
            "If specified, the separator used to split the input and output of the decoder. If not specified, the"
            " separator is a whitespace character."
        ),
    )
    context_sensitivity_std_threshold: float = cli_arg(
        default=1.0,
        help=(
            "Parameter to control the selection of ``output_current_text`` tokens considered as context-sensitive for "
            "moving onwards with attribution. Corresponds to the number of standard deviations above or below the mean"
            " ``context_sensitivity_metric`` score for tokens to be considered context-sensitive."
        ),
    )
    context_sensitivity_topk: Optional[int] = cli_arg(
        default=None,
        help=(
            "If set, after selecting the salient context-sensitive tokens with ``context_sensitivity_std_threshold`` "
            "only the top-K remaining tokens are used. By default no top-k selection is performed."
        ),
    )
    attribution_std_threshold: float = cli_arg(
        default=1.0,
        help=(
            "Parameter to control the selection of ``input_context_text`` and ``output_context_text`` tokens "
            "considered as salient as a result for the attribution process. Corresponds to the number of standard "
            "deviations above or below the mean ``attribution_method`` score for tokens to be considered salient. "
            "CCI scores for all context tokens are saved in the output, but this parameter controls which tokens are "
            "used in the visualization of context reliance."
        ),
    )
    attribution_topk: Optional[int] = cli_arg(
        default=None,
        help=(
            "If set, after selecting the most salient tokens with ``attribution_std_threshold`` "
            "only the top-K remaining tokens are used. By default no top-k selection is performed."
        ),
    )


@command_args_docstring
@dataclass
class AttributeContextOutputArgs:
    show_intermediate_outputs: bool = cli_arg(
        default=False,
        help=(
            "If specified, the intermediate outputs produced by the Inseq library for context-sensitive target "
            "identification (CTI) and contextual cues imputation (CCI) are shown during the process.",
        ),
    )
    save_path: Optional[str] = cli_arg(
        default=None,
        aliases=["-o"],
        help="If present, the output of the two-step process will be saved in JSON format at the specified path.",
    )
    add_output_info: bool = cli_arg(
        default=True,
        help="If specified, additional information about the attribution process is added to the saved output.",
    )
    viz_path: Optional[str] = cli_arg(
        default=None,
        help="If specified, the visualization produced from the output is saved in HTML format at the specified path.",
    )
    show_viz: bool = cli_arg(
        default=True,
        help="If specified, the visualization produced from the output is shown in the terminal.",
    )


@command_args_docstring
@dataclass
class AttributeContextArgs(AttributeContextInputArgs, AttributeContextMethodArgs, AttributeContextOutputArgs):
    def __repr__(self):
        return f"{self.__class__.__name__}({pretty_dict(self.__dict__)})"

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__.items())

    def __post_init__(self):
        if (
            self.handle_output_context_strategy == HandleOutputContextSetting.PRE.value
            and not self.output_context_text
            and "{context}" in self.output_template
        ):
            raise ValueError(
                "If --handle_output_context_strategy='pre' and {context} is used in --output_template, --output_context_text"
                " must be specified to avoid user prompt for output context."
            )
        if len(self.contextless_output_next_tokens) > 0 and self.prompt_user_for_contextless_output_next_tokens:
            raise ValueError(
                "Only one of contextless_output_next_tokens and prompt_user_for_contextless_output_next_tokens can be"
                " specified."
            )
        if self.input_template is None:
            self.input_template = "{current}" if self.input_context_text is None else "{context} {current}"
        if self.output_template is None:
            self.output_template = "{current}" if self.output_context_text is None else "{context} {current}"
        if self.contextless_input_current_text is None:
            self.contextless_input_current_text = "{current}"
        self.has_input_context = "{context}" in self.input_template
        self.has_output_context = "{context}" in self.output_template
        if not self.input_current_text:
            raise ValueError("--input_current_text must be a non-empty string.")
        if self.input_context_text and not self.has_input_context:
            logger.warning(
                f"input_template has format {self.input_template} (no {{context}}), but --input_context_text is"
                " specified. Ignoring provided --input_context_text."
            )
            self.input_context_text = None
        if self.output_context_text and not self.has_output_context:
            logger.warning(
                f"output_template has format {self.output_template} (no {{context}}), but --output_context_text is"
                " specified. Ignoring provided --output_context_text."
            )
            self.output_context_text = None
        if not self.input_context_text and self.has_input_context:
            raise ValueError(
                f"{{context}} format placeholder is present in input_template {self.input_template},"
                " but --input_context_text is not specified."
            )
        if "{current}" not in self.input_template:
            raise ValueError(f"{{current}} format placeholder is missing from input_template {self.input_template}.")
        if "{current}" not in self.output_template:
            raise ValueError(f"{{current}} format placeholder is missing from output_template {self.output_template}.")
        if not self.input_current_text:
            raise ValueError("--input_current_text must be a non-empty string.")
        if self.has_output_context and self.output_template.find("{context}") > self.output_template.find("{current}"):
            raise ValueError(
                f"{{context}} placeholder must appear before {{current}} in output_template '{self.output_template}'."
            )
        if not self.output_template.endswith("{current}"):
            *_, suffix = self.output_template.partition("{current}")
            logger.warning(
                f"Suffix '{suffix}' was specified in output_template and will be used to ignore the specified suffix"
                " tokens during context sensitivity detection. Make sure that the suffix corresponds to the end of the"
                " output_current_text by forcing --output_current_text if necessary."
            )
