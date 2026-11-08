import io
import sys
from types import ModuleType

import pytest
from PIL import Image

import app.services.extraction as extraction
from docx import Document as DocxDocument
from pptx import Presentation
from pptx.util import Inches
from pypdf import PdfWriter

from app.services.extraction import (
    _page_candidates,
    _ocr_text_for_candidate,
    _question_content,
    _split_candidates,
    detect_upload_mime,
    extract_candidates,
)


def test_splits_numbered_questions_and_keeps_choices_with_their_question():
    text = '1. Pick a color\nA) Red\nB) Blue\n\n2. Fill in: ___'

    candidates = _split_candidates(text)

    assert candidates == ['1. Pick a color\nA) Red\nB) Blue', '2. Fill in: ___']
    kind, blocks, confidence = _question_content(candidates[0])
    assert kind == 'multiple_choice'
    assert confidence is None
    assert [block['label'] for block in blocks if block['type'] == 'choice'] == ['A', 'B']

def test_short_response_commands_are_classified_as_short_answer():
    kind, _, _ = _question_content('1. What is imitation?')

    assert kind == 'short_answer'

def test_lowercase_graphing_subparts_are_not_misclassified_as_multiple_choice():
    kind, blocks, _ = _question_content(
        '6. For a relation R:\na. Draw the graph of R and R-1.\nb. State the universe of R.'
    )

    assert kind == 'short_answer'
    assert all(block['type'] != 'choice' for block in blocks)

def test_page_directions_are_preserved_as_context_not_as_a_question():
    candidates = _page_candidates(
        'I. Give short answer for the following questions.\n'
        '1. What is imitation?\n'
        '2. Define biology.',
        1,
        None,
        False,
    )

    assert len(candidates) == 2
    assert all(candidate['content']['page_context'].startswith('I.') for candidate in candidates)
    assert candidates[0]['text'] == '1. What is imitation?'


def test_section_directions_do_not_leak_into_adjacent_numbered_questions():
    candidates = _page_candidates(
        'Worksheet title\n'
        'I. Answer the questions.\n'
        '1. Define a vector.\n'
        '2. State its magnitude.\n'
        'II. Show all the necessary steps.\n'
        '3. Calculate the displacement.\n',
        1,
        None,
        False,
    )

    assert candidates[0]['text'] == '1. Define a vector.'
    assert candidates[1]['text'] == '2. State its magnitude.'
    assert candidates[2]['text'].endswith('3. Calculate the displacement.')
    assert candidates[1]['content']['page_context'].startswith('Worksheet title')
    assert 'II. Show all the necessary steps.' in candidates[2]['content']['page_context']

def test_ocr_alternative_is_kept_for_a_pdf_math_text_gap():
    candidates = _page_candidates(
        '1. What is the domain of f(x)= ?\n2. What is the value of x?',
        1,
        None,
        False,
        source_ocr_text='1. What is the domain of f(x)=x 4?\n3\n2. What is the value of x?',
        source_ocr_confidence=0.61,
    )

    assert candidates[0]['content']['source_ocr_text'] == '1. What is the domain of f(x)=x 4?\n3'
    assert candidates[0]['content']['source_ocr_confidence'] == 0.61
    assert 'pdf_text_layer_incomplete' in candidates[0]['signals']['reasons']
    assert 'source_ocr_text' not in candidates[1]['content']

def test_math_and_diagram_questions_are_marked_for_source_review():
    candidates = _page_candidates(
        '1. What is the domain and range of the function f(x)= ?\n2. Draw the graph of R and R-1.',
        1,
        0.61,
        True,
    )

    assert candidates[0]['content']['source_review_required'] is True
    assert candidates[0]['content']['source_review_kind'] == 'math_or_diagram'
    assert 'math_or_diagram_requires_source_review' in candidates[0]['signals']['reasons']
    assert 'original source page' in candidates[0]['text']
    assert candidates[1]['content']['source_review_required'] is True


def test_physics_diagrams_and_ambiguous_angle_symbols_require_source_review():
    candidates = _page_candidates(
        '1. Use a free body diagram to show the forces on the block.\n'
        '2. A car travels 25 km in a direction 600 west of north.',
        1,
        None,
        True,
    )

    assert candidates[0]['content']['source_review_kind'] == 'physics_symbols_or_diagram'
    assert 'physics_notation' in candidates[0]['content']['source_review_features']
    assert 'physics_source_review_required' in candidates[0]['signals']['reasons']
    assert candidates[1]['content']['source_review_kind'] == 'physics_symbols_or_diagram'
    assert 'ambiguous_angle_notation' in candidates[1]['content']['source_review_features']
    assert '600 west of north' in candidates[1]['text']


def test_physics_text_without_symbols_or_source_visuals_is_not_overflagged():
    candidate = _page_candidates(
        '1. What is the difference between collinear vectors and co-planar vectors?',
        1,
        None,
        False,
    )[0]

    assert 'source_review_required' not in candidate['content']

def test_ocr_candidate_text_ends_before_the_next_numbered_question():
    text = '1. Formula f(x)=x 4?\n3\n2. Next question'

    assert _ocr_text_for_candidate('1. Formula f(x)= ?', text) == '1. Formula f(x)=x 4?\n3'


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('Mark each statement true or false.', 'true_false'),
        ('Write the missing value: ____', 'fill_in_the_blank'),
        ('Briefly explain your reasoning.', 'short_answer'),
        ('Discuss the following.', 'unknown'),
    ],
)
def test_classifies_supported_question_formats_without_guessing(text, expected):
    kind, _, confidence = _question_content(text)

    assert kind == expected
    assert confidence is None


def test_empty_page_becomes_source_fallback_candidate():
    candidate = _page_candidates('', 3, None, False)[0]

    assert candidate['question_type'] == 'unknown'
    assert candidate['content']['visual_fallback'] is True
    assert candidate['signals']['requires_review'] is True
    assert candidate['signals']['reasons'] == ['no_readable_text']


def test_docx_preserves_paragraph_breaks_and_tables():
    document = DocxDocument()
    document.add_paragraph('1. Choose an option')
    document.add_paragraph('A) First')
    document.add_paragraph('B) Second')
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = 'Label'
    table.cell(0, 1).text = 'Value'
    output = io.BytesIO()
    document.save(output)

    page_count, candidates = extract_candidates(
        output.getvalue(),
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )

    assert page_count is None
    assert len(candidates) == 1
    candidate_text = candidates[0]['text']
    assert candidates[0]['question_type'] == 'multiple_choice'
    assert all(candidate['content']['visual_fallback'] for candidate in candidates)
    assert 'Label | Value' in candidate_text


def test_pptx_extracts_slide_text_and_slide_number():
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    shape = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(1))
    shape.text = '1. Briefly explain the result.'
    output = io.BytesIO()
    presentation.save(output)

    page_count, candidates = extract_candidates(
        output.getvalue(),
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    )

    assert page_count == 1
    assert candidates[0]['content']['source_page'] == 1
    assert candidates[0]['question_type'] == 'short_answer'


def test_pdf_fallback_preserves_blank_page_as_source_review_item():
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    output = io.BytesIO()
    writer.write(output)

    page_count, candidates = extract_candidates(output.getvalue(), 'application/pdf')

    assert page_count == 1
    assert candidates[0]['content']['source_page'] == 1
    assert candidates[0]['signals']['requires_review'] is True


def test_image_without_local_ocr_is_retained_for_source_review():
    output = io.BytesIO()
    Image.new('RGB', (32, 32), 'white').save(output, format='PNG')

    page_count, candidates = extract_candidates(output.getvalue(), 'image/png')

    assert page_count == 1
    assert candidates[0]['content']['visual_fallback'] is True
    assert candidates[0]['signals']['requires_review'] is True


def test_local_ocr_engine_text_and_confidence_are_preserved(monkeypatch):
    class FakeEngine:
        def __call__(self, _image):
            return [([[0, 0], [1, 0], [1, 1], [0, 1]], 'Recognized text', 0.94)], None

    module = ModuleType('rapidocr_onnxruntime')
    module.RapidOCR = FakeEngine
    monkeypatch.setitem(sys.modules, 'rapidocr_onnxruntime', module)
    monkeypatch.setattr(extraction, '_ocr_engine', None)

    recognized, confidence, regions = extraction._ocr_text(Image.new('RGB', (32, 32), 'white'))

    assert recognized == 'Recognized text'
    assert confidence == 0.94
    assert regions == [{
        'text': 'Recognized text',
        'bbox': [0.0, 0.0, 0.03125, 0.03125],
        'confidence': 0.94,
    }]


def test_ocr_source_regions_are_attached_to_the_matching_question_only():
    regions = [
        {'text': '1. First question', 'bbox': [0.1, 0.1, 0.6, 0.2], 'confidence': 0.98},
        {'text': '2. Second question', 'bbox': [0.1, 0.5, 0.7, 0.6], 'confidence': 0.91},
    ]

    candidates = _page_candidates(
        '1. First question\n\n2. Second question',
        4,
        0.91,
        False,
        regions,
        (1000, 2000),
    )

    assert len(candidates) == 2
    assert candidates[0]['content']['source_regions'] == regions[:1]
    assert candidates[1]['content']['source_regions'] == regions[1:]
    assert candidates[1]['content']['source_coordinate_space'] == 'normalized_page_image'
    assert candidates[1]['content']['source_image_size'] == [1000, 2000]


def test_pdf_without_renderer_marks_blank_page_for_source_review():
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    output = io.BytesIO()
    writer.write(output)

    page_count, candidates = extraction._read_pdf_with_pypdf(output.getvalue())

    assert page_count == 1
    assert candidates[0]['signals']['reasons'] == ['local_ocr_unavailable']


def test_upload_mime_detection_rejects_mismatched_magic_bytes():
    with pytest.raises(ValueError, match='not a supported'):
        detect_upload_mime(b'not a PDF')
