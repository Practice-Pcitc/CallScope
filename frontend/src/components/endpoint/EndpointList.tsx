import { ApiOutlined, SearchOutlined } from "@ant-design/icons";
import {
  Button,
  Checkbox,
  Empty,
  Input,
  Select,
  Space,
  Spin,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { useEffect, useMemo } from "react";
import { useParams } from "react-router-dom";

import { useEndpointStore } from "../../stores/endpointStore";
import { useProjectStore } from "../../stores/projectStore";
import type { HttpMethod } from "../../types/endpoint";
import { cleanDisplayText } from "../../utils/displayText";

const { Text, Title } = Typography;

const methodColors: Record<HttpMethod, string> = {
  GET: "green",
  POST: "blue",
  PUT: "orange",
  DELETE: "red",
  PATCH: "purple",
  OPTIONS: "cyan",
  HEAD: "default",
};

const methodOptions = [
  { value: "ALL", label: "全部方法" },
  ...(["GET", "POST", "PUT", "DELETE", "PATCH"] as HttpMethod[]).map(
    (method) => ({ value: method, label: method }),
  ),
];

export function EndpointList() {
  const { projectId } = useParams();
  const activeRevisionId = useProjectStore(
    (state) => state.activeProject?.activeRevisionId,
  );
  const {
    endpoints,
    modules,
    total,
    selectedIds,
    activeEndpointId,
    filters,
    loading,
    fetchEndpoints,
    setSearch,
    setHttpMethod,
    setModule,
    toggleSelected,
    selectEndpoint,
    selectAll,
    clearSelection,
  } = useEndpointStore();
  const groupedEndpoints = useMemo(
    () =>
      Object.entries(
        endpoints.reduce<Record<string, typeof endpoints>>(
          (groups, endpoint) => {
            const category = cleanDisplayText(endpoint.moduleName, "未分类");
            groups[category] = [...(groups[category] ?? []), endpoint];
            return groups;
          },
          {},
        ),
      ),
    [endpoints],
  );

  useEffect(() => {
    if (!projectId) {
      return;
    }
    const timer = window.setTimeout(() => {
      void fetchEndpoints(projectId).catch(() => undefined);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [
    activeRevisionId,
    fetchEndpoints,
    filters.httpMethod,
    filters.module,
    filters.search,
    projectId,
  ]);

  return (
    <div className="panel-content endpoint-panel">
      <div className="panel-heading">
        <Title level={5}>接口列表</Title>
        <span className="count-badge">{total}</span>
      </div>

      <Input
        value={filters.search}
        onChange={(event) => setSearch(event.target.value)}
        prefix={<SearchOutlined />}
        placeholder="搜索路径或函数"
        allowClear
      />

      <Space.Compact block>
        <Select
          value={filters.httpMethod}
          options={methodOptions}
          onChange={(value) => setHttpMethod(value)}
          style={{ width: "42%" }}
        />
        <Select
          value={filters.module}
          options={[
            { value: "", label: "全部业务分类" },
            ...modules.map((module) => ({
              value: module,
              label: cleanDisplayText(module, "未分类"),
            })),
          ]}
          onChange={setModule}
          style={{ width: "58%" }}
          popupMatchSelectWidth={300}
        />
      </Space.Compact>

      <div className="endpoint-selection-bar">
        <Text type="secondary">已选 {selectedIds.length}</Text>
        <Space size={4}>
          <Button type="link" size="small" onClick={selectAll}>
            全选
          </Button>
          <Button type="link" size="small" onClick={clearSelection}>
            清空
          </Button>
        </Space>
      </div>

      <div className="endpoint-list-scroll">
        <Spin spinning={loading} className="endpoint-list-spinner">
          <div className="endpoint-list">
            {endpoints.length === 0 ? (
              <Empty
                image={<ApiOutlined className="empty-icon" />}
                description={
                  <Space direction="vertical" size={4}>
                    <Text>
                      {activeRevisionId ? "未识别到接口" : "还没有接口数据"}
                    </Text>
                    <Text type="secondary">
                      {activeRevisionId
                        ? "检查项目中是否存在受支持的 FastAPI 或 Spring 路由"
                        : "先启动项目扫描"}
                    </Text>
                  </Space>
                }
              />
            ) : (
              groupedEndpoints.map(([category, categoryEndpoints]) => (
                <section className="endpoint-category-group" key={category}>
                  <div className="endpoint-category-heading">
                    <Text>{category}</Text>
                    <span>{categoryEndpoints.length}</span>
                  </div>
                  {categoryEndpoints.map((endpoint) => (
                    <div
                      key={endpoint.id}
                      className={`endpoint-item ${
                        activeEndpointId === endpoint.id ? "active" : ""
                      }`}
                      onClick={() => selectEndpoint(endpoint.id)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          selectEndpoint(endpoint.id);
                        }
                      }}
                    >
                      <Checkbox
                        checked={selectedIds.includes(endpoint.id)}
                        onClick={(event) => event.stopPropagation()}
                        onChange={() => toggleSelected(endpoint.id)}
                      />
                      <div className="endpoint-item-body">
                        <div className="endpoint-item-route">
                          <Tag color={methodColors[endpoint.httpMethod]}>
                            {endpoint.httpMethod}
                          </Tag>
                          <Tooltip title={endpoint.path}>
                            <Text ellipsis>{endpoint.path}</Text>
                          </Tooltip>
                        </div>
                        <Text className="endpoint-function" ellipsis>
                          {cleanDisplayText(
                            endpoint.summary,
                            endpoint.functionName,
                          )}
                        </Text>
                        <Tooltip
                          title={`${endpoint.filePath}:${endpoint.startLine}`}
                        >
                          <Text
                            type="secondary"
                            ellipsis
                            className="endpoint-file"
                          >
                            {endpoint.filePath}:{endpoint.startLine}
                          </Text>
                        </Tooltip>
                      </div>
                    </div>
                  ))}
                </section>
              ))
            )}
          </div>
        </Spin>
      </div>
    </div>
  );
}
