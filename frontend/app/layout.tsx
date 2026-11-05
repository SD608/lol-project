import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PICKOU | 픽의 이유를 찾다",
  description: "리그 오브 레전드 챔피언 상성 조회. 근거 없는 등급과 승률은 표시하지 않습니다.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ko"><body>{children}</body></html>;
}
