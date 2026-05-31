import { AntdRegistry } from "@ant-design/nextjs-registry";
import type { ReactNode } from "react";
import { AppShell } from "./AppShell";
import "./globals.css";

export const metadata = { title: "Knock Knock" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AntdRegistry>
          <AppShell>{children}</AppShell>
        </AntdRegistry>
      </body>
    </html>
  );
}
