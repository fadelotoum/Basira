"""Basira Control Center — local project dashboard."""

import cv2
import numpy as np
import streamlit as st
from PIL import Image

from basira.analysis import BasiraAnalyzer


st.set_page_config(page_title="Basira Control Center", page_icon="👁️", layout="wide")


@st.cache_resource(show_spinner="Loading Basira AI models...")
def get_analyzer() -> BasiraAnalyzer:
    """Load expensive AI models once per dashboard session."""
    return BasiraAnalyzer()


def to_bgr(image: Image.Image) -> np.ndarray:
    """Convert an uploaded image into the format OpenCV expects."""
    rgb = np.array(image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


st.title("Basira Control Center")
st.caption("Real-time obstacle awareness prototype | MacBook AI processing")

with st.sidebar:
    st.header("System status")
    st.success("Object detection ready")
    st.success("Relative-depth estimation ready")
    st.info("Live iPhone Ultra Wide streaming: upcoming")
    st.divider()
    st.caption("Safety scope: awareness prototype only. Not a navigation guarantee.")

left, right = st.columns([1.35, 1])

with left:
    st.subheader("Test image")
    uploaded_file = st.file_uploader("Upload a room or obstacle image", type=["jpg", "jpeg", "png"])
    captured_file = st.camera_input("Or take a test image from this Mac")

with right:
    st.subheader("Detection report")
    report = st.empty()

selected_file = uploaded_file or captured_file

if selected_file:
    source_image = Image.open(selected_file)
    bgr_frame = to_bgr(source_image)

    with st.spinner("Analyzing scene..."):
        annotated_frame, findings = get_analyzer().analyze(bgr_frame)

    st.image(cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB), caption="Basira analysis", use_container_width=True)

    with right:
        if findings:
            report.metric("Objects detected", len(findings))
            for detection, risk in findings:
                st.markdown(
                    f"**{detection.label.title()}**  \\n+                    {risk.proximity} · {risk.level} risk · {detection.confidence:.0%} confidence"
                )
        else:
            report.warning("No supported object was detected in this image.")
else:
    st.info("Upload a test image or take one from the Mac camera to start a Basira analysis.")
