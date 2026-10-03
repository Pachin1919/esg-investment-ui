# Green Street · Green-value Investment Analysis

面向投资者的绿色值投资分析原型：理解公司环保表现与投资收益预期之间的关系，并模拟组合调整。

## 页面与核心流程

- `/`：绿色 Landing Page，介绍环境表现如何可能影响成本、转型风险与投资收益预期。
- `/app`：蓝色分析工作台，展示组合指标、股票候选与模拟比较。
- 首页流程：设置偏好 → 导入组合 → 查看股票推荐 → 比较新旧组合。
- 工作台主导航：Current portfolio、Recommendations、Settings；指标说明直接在指标和公司名称旁查看，不再设独立 Methodology 页面。
- 兼容旧演示地址：`/?v=blue` 进入样例工作台，`/?v=green` 显示首页。

## 本地运行

使用 Node.js 22.12+：

```powershell
npm ci
npm run dev
```

当前终端已经位于项目根目录时，无需再次执行 `cd esg-investment-ui`。打开 <http://127.0.0.1:4319/>。Windows 也可运行 `.\start-demo.cmd`。

```powershell
npm run build
npm run preview
```

## 已实现

- CSV 内容解析、逐行校验、导入预览与报告币种设置。
- 使用当前持仓市值计算权重；支持报告已归一化币种及自动换汇，用户不需要输入汇率。
- 五档风险承受度，按绿、蓝、黄、橙、红可视化；五档绿色偏好。
- 组合预期收益、绿色评分、可选波动率的指标卡。
- 公司详情突出 Expected return 和 E-score。
- 根据风险、绿色偏好和最高投资金额动态筛选及排序候选；关键词搜索仅返回推荐公司。
- 按整数股数或金额预算模拟，展示单价 × 股数 = 总价；金额模式自动向下取整并展示未使用预算。
- 新增资金模式，以及按整数股数减持并可补充资金的再平衡模式。
- 新旧组合金额、收益、绿色评分、数据覆盖率及每家公司单价、股数、总价和权重比较。
- 公司名称与组合指标支持鼠标悬浮、键盘聚焦和点击解释。
- 当前组合、推荐组合及新旧对比可导出分页 PDF 报表；推荐及对比保留 JSON 结构化导出。
- 本地保存持仓、偏好和模拟草稿，支持导出与清除。
- 键盘可操作对话框、响应式布局和减少动态效果。

## 数据边界

真实 API 和后端计算契约尚未提供。目前行情、公司评分、收益预期及交叉汇率由 `src/marketData.ts` 的本地数据提供，后续可替换为真实数据服务。推荐筛选和排序在 `recommendStocks` 中基于 Settings 动态计算，不是经过验证的投资优化模型。

CSV 可提供 `units` / `quantity` / `shares` 和 `unit_price` / `price`。只有确切数量或能按价格精确推导的整数数量才显示股数；不凭空补齐未知持仓数量。已识别公司可匹配本地行情，其他公司指标保持不可用。单位价格保留换汇精度，总额按两位小数展示。波动率尚未提供。

最新 Q&A 明确风险与绿色偏好均可使用 1–5 档；5 分别表示更高风险承受度和更强绿色偏好。颜色不是机构信用评级或资产风险结论。

环境评分越高表示越环保，不代表收益更高或投资更好。最终评分范围与组合聚合方法待确认；演示使用 0–10。年预期收益为拟采用展示方式，详细口径仍待后端确认。波动率尚未提供，UI 不伪造该数值。

本轮不使用 E_weight，也不使用依赖它的旧 greenness 公式。没有历史趋势、行业对比或组合预测图。

本地导入数据与模拟草稿保存于浏览器 localStorage，可使用 Clear portfolio 清除。没有账户连接、交易或支付。

## 结构

```text
src/App.tsx          绿色首页、首页与工作台路由切换
src/Workbench.tsx    导入、偏好、指标、推荐、公司详情与模拟流程
src/portfolio.ts     CSV 解析、币种归一化、样例与本地金额/权重演示
src/marketData.ts    可替换的本地行情、公司数据及自动汇率服务
src/InfoPopover.tsx 公司绿色评分与组合指标解释
src/portfolioExport.ts  分页 PDF 报表及 JSON 导出
src/styles.css      原视觉系统与基础布局
src/analysis.css    分析页面、风险配色、可读性和响应式补充
docs/api-examples/  暂定契约、导入样例和虚构 JSON
```

技术栈：React 19、TypeScript、Vite、Phosphor Icons、原生 CSS。

参见 [演示指南](docs/demo-guide.md) 与 [暂定接口和样例](docs/api-examples/README.md)。
