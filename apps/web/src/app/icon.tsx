import { ImageResponse } from "next/og";
export const size = { width: 32, height: 32 };
export const contentType = "image/png";
export default function Icon() {
  return new ImageResponse(
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
        background: "#1b1e22",
        color: "#f1f2f3",
        border: "1px solid #3a4048",
        borderRadius: 7,
        fontSize: 24,
        fontWeight: 700,
      }}
    >
      B
    </div>,
    size,
  );
}
