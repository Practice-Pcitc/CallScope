import { FolderOpenOutlined } from "@ant-design/icons";
import { Alert, Form, Input, Modal, Typography } from "antd";

import type { ProjectCreate } from "../../types/project";

const { Paragraph, Text } = Typography;

interface ProjectImportModalProps {
  open: boolean;
  loading: boolean;
  onCancel: () => void;
  onSubmit: (payload: ProjectCreate) => Promise<void>;
}

export function ProjectImportModal({
  open,
  loading,
  onCancel,
  onSubmit,
}: ProjectImportModalProps) {
  const [form] = Form.useForm<ProjectCreate>();

  const handleSubmit = async () => {
    const values = await form.validateFields();
    await onSubmit(values);
    form.resetFields();
  };

  return (
    <Modal
      title="导入本地后端项目"
      open={open}
      confirmLoading={loading}
      okText="导入项目"
      cancelText="取消"
      onCancel={onCancel}
      onOk={handleSubmit}
      destroyOnHidden
    >
      <Paragraph type="secondary">
        填写运行 CallScope 的这台电脑上的绝对目录。系统只进行静态文件遍历，
        不会执行项目代码。
      </Paragraph>
      <Alert
        type="info"
        showIcon
        message="支持 Python FastAPI 与 Java Spring Boot；只做静态分析，不会编译或执行目标项目。"
        style={{ marginBottom: 20 }}
      />
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item
          name="name"
          label="项目名称"
          rules={[
            { required: true, message: "请输入项目名称" },
            { max: 120, message: "项目名称最多 120 个字符" },
          ]}
        >
          <Input placeholder="例如：用户中心服务" autoFocus />
        </Form.Item>
        <Form.Item
          name="rootPath"
          label="项目绝对路径"
          extra={
            <Text type="secondary">Windows 示例：D:\work\user-service</Text>
          }
          rules={[{ required: true, message: "请输入项目绝对路径" }]}
        >
          <Input
            prefix={<FolderOpenOutlined />}
            placeholder="D:\work\my-backend-project"
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
