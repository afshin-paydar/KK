"use client";

import type { Device, DeviceRegistered } from "@kk/contracts";
import { Alert, Button, Card, Form, Input, Space, Table, Typography } from "antd";
import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";

export function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [registered, setRegistered] = useState<DeviceRegistered | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form] = Form.useForm<{ name: string }>();

  const refresh = () =>
    api
      .listDevices()
      .then(setDevices)
      .catch((e) => setError(String(e)));

  useEffect(() => {
    refresh();
  }, []);

  async function onFinish(values: { name: string }) {
    try {
      const result = await api.registerDevice({ name: values.name });
      setRegistered(result); // enrollment token is shown exactly once
      form.resetFields();
      refresh();
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <Space direction="vertical" size="middle" className="w-full">
      <Typography.Title level={2}>Fleet</Typography.Title>

      {error && (
        <Alert type="error" message={error} closable onClose={() => setError(null)} />
      )}

      <Form form={form} layout="inline" onFinish={onFinish}>
        <Form.Item name="name" rules={[{ required: true, message: "Required" }]}>
          <Input placeholder="Device name" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit">
            Register
          </Button>
        </Form.Item>
      </Form>

      {registered && (
        <Card className="bg-yellow-50" size="small">
          <Typography.Text strong>Enrollment token (shown once):</Typography.Text>
          <Typography.Paragraph
            code
            copyable
            className="break-all !mt-2"
          >
            {registered.enrollment_token}
          </Typography.Paragraph>
          <Typography.Text type="secondary">
            Provision this onto {registered.device.name} before{" "}
            {registered.enrollment_expires_at}.
          </Typography.Text>
        </Card>
      )}

      <Table<Device>
        rowKey="id"
        dataSource={devices}
        pagination={false}
        columns={[
          { title: "Name", dataIndex: "name" },
          { title: "Status", dataIndex: "status" },
          {
            title: "Agent",
            dataIndex: "agent_version",
            render: (v: string | null) => v ?? "—",
          },
          {
            title: "Last seen",
            dataIndex: "last_seen_at",
            render: (v: string | null) => v ?? "never",
          },
          {
            title: "",
            key: "actions",
            render: (_, d) =>
              d.status !== "revoked" && (
                <Button
                  danger
                  size="small"
                  onClick={() => api.revokeDevice(d.id).then(refresh)}
                >
                  Revoke
                </Button>
              ),
          },
        ]}
      />
    </Space>
  );
}
