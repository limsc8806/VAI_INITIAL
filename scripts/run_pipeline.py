#!/usr/bin/env python

from vai_plan.pipeline import main, run_pipeline

if __name__ == "__main__":
    # 기본 파이프라인 실행 (configs/default.yaml, sample_ddr5.pdf)
    main()

    # 아래는 직접 파이프라인 결과를 받아서 후처리/검증하는 예시입니다.
    # result = run_pipeline(config_path=Path("configs/default.yaml"), pdf_path=None)
    # print("Pipeline run result:", result)
