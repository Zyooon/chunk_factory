from apps.analysis_rag.service import generate_analysis_result


def main() -> None:
    sample_result = generate_analysis_result(
        gender="남성",
        face_shape="둥근형",
        face_proportion="균형",
        recommended_hair_styles=[
            {
                "style_name": "리프",
                "style_code": "m-09",
            },
            {
                "style_name": "퀴프",
                "style_code": "m-10",
            },
            {
                "style_name": "댄디",
                "style_code": "m-08",
            },
        ],
    )

    print(sample_result)


if __name__ == "__main__":
    main()