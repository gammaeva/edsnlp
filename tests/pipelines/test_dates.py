from dateparser import DateDataParser
from pytest import fixture, raises
from datetime import date, timedelta, datetime

from edsnlp.pipelines.dates import Dates, terms


@fixture(scope="session")
def parser():
    return DateDataParser(languages=["fr"])


def test_parser_absolute(parser: DateDataParser):
    tests = [
        ("le 3 juillet 2020", date(2020, 7, 3)),
        ("le 3/7/2020", date(2020, 7, 3)),
        ("le 03 07 20", date(2020, 7, 3)),
        ("03/07/2020", date(2020, 7, 3)),
        ("03.07.20", date(2020, 7, 3)),
        ("1er juillet 2021", date(2021, 7, 1)),
        # ("le premier juillet 2021", date(2021, 7, 1)),
    ]

    for test, answer in tests:
        assert parser.get_date_data(test).date_obj.date() == answer


def test_parser_relative(parser: DateDataParser):
    tests = [
        ("hier", [timedelta(days=-1)]),
        (
            "le mois dernier",
            [
                timedelta(days=-31),
                timedelta(days=-30),
                timedelta(days=-29),
                timedelta(days=-28),
            ],
        ),
        ("il y a trois jours", [timedelta(days=-3)]),
        ("l'année dernière", [timedelta(days=-365), timedelta(days=-366)]),
        # ("l'an dernier", timedelta(days=-365)),
    ]

    for test, answers in tests:
        assert any(
            [
                parser.get_date_data(test).date_obj.date() == (date.today() + a)
                for a in answers
            ]
        )


text = (
    "Le patient est venu hier (le 04/09/2021) pour un test PCR.\n"
    "Il est cas contact depuis la semaine dernière, le 09/08 (2021-08-09)."
)


@fixture
def dates(nlp):
    return Dates(
        nlp,
        absolute=terms.absolute,
        full_date=terms.full_date,
        relative=terms.relative,
        no_year=terms.no_year,
        false_positive=terms.false_positives,
    )


def test_dateparser_failure_cases(blank_nlp, dates, parser: DateDataParser):
    examples = [
        "le premier juillet 2021",
        "l'an dernier",
    ]

    for example in examples:
        assert parser.get_date_data(example).date_obj is None

        doc = blank_nlp(example)
        doc = dates(doc)

        d = doc.spans["dates"][0]

        assert d._.date == "????-??-??"


def test_dates_component(blank_nlp, dates):

    doc = blank_nlp(text)

    with raises(KeyError):
        doc.spans["dates"]

    doc = dates(doc)

    d1, d2, d3, d4, d5 = doc.spans["dates"]

    assert d1._.date == "TD-1"
    assert d2._.date == "2021-09-04"
    assert d3._.date == "TD-7"
    assert d4._.date == "????-08-09"
    assert d5._.date == "2021-08-09"


def test_dates_with_base_date(blank_nlp, dates):

    doc = blank_nlp(text)
    doc = dates(doc)

    doc._.note_datetime = datetime(2020, 10, 10)

    d1, d2, d3, d4, d5 = doc.spans["dates"]

    assert d1._.date == "2020-10-09"
    assert d2._.date == "2021-09-04"
    assert d3._.date == "2020-10-03"
    assert d4._.date == "2020-08-09"
    assert d5._.date == "2021-08-09"


def test_absolute_dates_patterns(blank_nlp, dates):

    examples = [
        ("Objet : Consultation du 03 07 19", "2019-07-03"),
        ("Objet : Consultation du 03 juillet 19", "2019-07-03"),
        ("Objet : Consultation du 3 juillet 19", "2019-07-03"),
        ("Objet : Consultation du 03-07-19", "2019-07-03"),
        ("Objet : Consultation du 03-07-1993", "1993-07-03"),
        ("Objet : Consultation du 1993-12-02", "1993-12-02"),
    ]

    for example, answer in examples:
        doc = blank_nlp(example)
        doc = dates(doc)

        date = doc.spans["dates"][0]

        assert date._.date == answer


def test_patterns(blank_nlp, dates):

    examples = [
        "Le patient est venu en 2019 pour une consultation",
        "Le patient est venu le 1er septembre pour une consultation",
        "Le patient est venu en octobre 2020 pour une consultation",
        "Le patient est venu il y a trois mois pour une consultation",
        "Le patient est venu il y a un an pour une consultation",
        "Il lui était arrivé la même chose il y a un an.",
        "Le patient est venu le 20/09/2001 pour une consultation",
        "Objet : Consultation du 03 07 19",
    ]

    for example in examples:
        doc = blank_nlp(example)
        doc = dates(doc)

        assert len(doc.spans["dates"]) == 1


def test_false_positives(blank_nlp, dates):

    counter_examples = [
        "40 00",
        "06 12 34 56 78",
        "bien mais",
        "thierry",
        "436",
    ]

    for example in counter_examples:
        doc = blank_nlp(example)
        doc = dates(doc)

        assert len(doc.spans["dates"]) == 0