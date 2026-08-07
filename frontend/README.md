# CallScope Frontend

## 开发启动

```powershell
npm.cmd install
npm.cmd run dev
```

默认访问 `http://localhost:5173`。开发服务器会将 `/api` 请求代理到
`http://127.0.0.1:8000`。

在左侧选择接口后，画布会加载第一层拓扑。双击节点展开或折叠，滚轮缩放，
拖动画布或节点；点击节点和关系可在右侧查看源码证据。多选接口时会自动合并
拓扑并标识公共节点。

## 验证

```powershell
npm.cmd run typecheck
npm.cmd run build
```
