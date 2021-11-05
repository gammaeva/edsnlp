from typing import Any, Dict, List

from loguru import logger
from spacy.language import Language
from spacy.tokens import Doc, Span
from spacy.util import filter_spans

from edsnlp.pipelines.matcher import GenericMatcher


class Sections(GenericMatcher):
    """
    Divides the document into sections.

    By default, we are using a dataset of documents annotated for section titles,
    using the work done by Ivan Lerner, reviewed by Gilles Chatellier.

    Detected sections are :

    - allergies ;
    - antécédents ;
    - antécédents familiaux ;
    - traitements entrée ;
    - conclusion ;
    - conclusion entrée ;
    - habitus ;
    - correspondants ;
    - diagnostic ;
    - données biométriques entrée ;
    - examens ;
    - examens complémentaires ;
    - facteurs de risques ;
    - histoire de la maladie ;
    - actes ;
    - motif ;
    - prescriptions ;
    - traitements sortie.

    The component looks for section titles within the document,
    and stores them in the `section_title` extension.

    For ease-of-use, the component also populates a `section` extension,
    which contains a list of spans corresponding to the "sections" of the
    document. These span from the start of one section title to the next,
    which can introduce obvious bias should an intermediate section title
    goes undetected.

    Parameters
    ----------
    nlp:
        Spacy pipeline object.
    sections:
        Dictionary of terms to look for
    add_newline:
        Whether to add a new line character before each expression, to improve precision.

    Other Parameters
    ----------------
    fuzzy:
        Whether to use fuzzy matching. Be aware, this significantly increases compute time.
    """

    def __init__(
        self,
        nlp: Language,
        sections: Dict[str, List[str]],
        add_patterns: bool,
        attr: str,
        fuzzy: bool,
        fuzzy_kwargs: Dict[str, Any],
    ):

        logger.warning(
            "The component Sections is still in Beta. Use at your own risks."
        )

        self.add_patterns = add_patterns
        if add_patterns:
            for k, v in sections.items():
                sections[k] = [r"\n[^\n]{0,5}" + ent + r"[^\n]{0,5}\n" for ent in v]

        super().__init__(
            nlp,
            terms=None,
            regex=sections,
            attr=attr,
            fuzzy=fuzzy,
            fuzzy_kwargs=fuzzy_kwargs,
            filter_matches=True,
            on_ents_only=False,
        )

        if not Span.has_extension("section_title"):
            Span.set_extension("section_title", default=None)

        if not Span.has_extension("section"):
            Span.set_extension("section", default=None)

        if not nlp.has_pipe("normalizer"):
            logger.warning("You should add pipe `normalizer`")

    # noinspection PyProtectedMember
    def __call__(self, doc: Doc) -> Doc:
        """
        Divides the doc into sections

        Parameters
        ----------
        doc:
            spaCy Doc object

        Returns
        -------
        doc:
            spaCy Doc object, annotated for sections
        """
        titles = filter_spans(self.process(doc))

        if self.add_patterns:
            # Remove preceding newline
            titles = [
                Span(doc, title.start + 1, title.end - 1, label=title.label_)
                for title in titles
            ]

        sections = []
        print(titles)
        for t1, t2 in zip(titles[:-1], titles[1:]):
            section = Span(doc, t1.start, t2.start, label=t1.label)
            section._.section_title = t1
            sections.append(section)

        if titles:
            t = titles[-1]
            section = Span(doc, t.start, len(doc), label=t.label)
            section._.section_title = t
            sections.append(section)

        doc.spans["sections"] = sections
        doc.spans["section_titles"] = titles

        return doc
