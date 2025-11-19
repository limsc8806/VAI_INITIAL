"""
간단한 Docling 테스트 스크립트
test_img_table.pdf로 테이블/그림 추출 성능 확인
"""
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
import json

def test_docling_extraction():
    # PDF 경로
    pdf_path = Path("data/raw/test_img_table.pdf")
    
    # Docling 옵션 설정
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False  # 먼저 OCR 없이 테스트
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    
    # Converter 생성
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                backend=PyPdfiumDocumentBackend
            )
        }
    )
    
    print(f"PDF 파일: {pdf_path}")
    print("="*60)
    
    # PDF 변환
    result = converter.convert(pdf_path)
    
    # 기본 정보 출력
    print(f"\n📄 문서 정보:")
    print(f"  - 페이지 수: {len(result.document.pages)}")
    print(f"  - 파일명: {result.input.file.name}")
    
    # 테이블 추출 결과
    print(f"\n📊 테이블 추출:")
    print(f"  - 테이블 개수: {len(result.document.tables)}")
    
    for idx, table in enumerate(result.document.tables, 1):
        print(f"\n  테이블 #{idx}:")
        print(f"    - 페이지: {table.prov[0].page_no if table.prov else 'N/A'}")
        print(f"    - 행/열: {table.data.num_rows} x {table.data.num_cols}")
        print(f"    - 셀 개수: {len(table.data.table_cells)}")
        
        # 첫 5개 셀만 출력
        if table.data.table_cells:
            print(f"    - 샘플 셀:")
            for cell in table.data.table_cells[:5]:
                print(f"      [{cell.start_row_offset_idx},{cell.start_col_offset_idx}]: {cell.text[:30]}")
    
    # 그림 추출 결과
    print(f"\n🖼️  그림 추출:")
    pictures = [item for item in result.document.body if hasattr(item, '__class__') and 
                item.__class__.__name__ == 'PictureItem']
    print(f"  - 그림 개수: {len(pictures)}")
    
    for idx, pic in enumerate(pictures, 1):
        print(f"\n  그림 #{idx}:")
        if pic.prov:
            prov = pic.prov[0]
            print(f"    - 페이지: {prov.page_no}")
            print(f"    - Bbox: ({prov.bbox.l:.1f}, {prov.bbox.t:.1f}, "
                  f"{prov.bbox.r:.1f}, {prov.bbox.b:.1f})")
    
    # 레이아웃 요소 분석
    print(f"\n📐 레이아웃 분석:")
    layout_types = {}
    for item in result.document.body:
        item_type = item.__class__.__name__
        layout_types[item_type] = layout_types.get(item_type, 0) + 1
    
    for item_type, count in sorted(layout_types.items()):
        print(f"  - {item_type}: {count}")
    
    # JSON 저장 (디버깅용)
    output_path = Path("_docling_test_output.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        # Docling 결과를 JSON으로 직렬화
        doc_dict = result.document.export_to_dict()
        json.dump(doc_dict, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 결과를 {output_path}에 저장했습니다.")
    
    # Markdown 출력 샘플
    print("\n📝 Markdown 샘플 (처음 500자):")
    print("="*60)
    md_output = result.document.export_to_markdown()
    print(md_output[:500])
    print("="*60)

if __name__ == "__main__":
    test_docling_extraction()
