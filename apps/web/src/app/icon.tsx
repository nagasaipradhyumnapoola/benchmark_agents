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
        background: "#111211",
        color: "#eeede9",
        borderRadius: 3,
        fontSize: 16,
        fontWeight: 650,
        letterSpacing: -1,
      }}
    >
      BA
    </div>,
    size,
  );
}
