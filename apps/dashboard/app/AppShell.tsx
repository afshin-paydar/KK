"use client";

import { ConfigProvider, Layout, Typography } from "antd";
import Link from "next/link";
import type { ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <ConfigProvider>
      <Layout className="min-h-screen">
        <Layout.Header className="flex items-center gap-4 bg-white border-b border-gray-200 px-6">
          <Typography.Title level={3} className="!mb-0 !mr-auto">
            Knock Knock
          </Typography.Title>
          <Link href="/">Devices</Link>
          <Link href="/policies">Policies</Link>
        </Layout.Header>
        <Layout.Content className="max-w-5xl w-full mx-auto p-6">
          {children}
        </Layout.Content>
      </Layout>
    </ConfigProvider>
  );
}
