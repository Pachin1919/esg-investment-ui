# Green Street · ESG UI Demo

2026-10-03 · 两个可运行的前端版本。产品名称已确认为 Green Street。

## 预览

```powershell
cd esg-investment-ui
npm ci
npm run dev
```

也可以双击 `start-demo.cmd`。保持启动终端运行，然后打开：

- 浅蓝版 Clarity：<http://127.0.0.1:4319/?v=blue>
- 浅绿版 Sage：<http://127.0.0.1:4319/?v=green>

顶部可以随时切换两个版本。地址是本机预览，不能直接发送给同事作为公网链接。

## 两个版本

1. **Clarity blue**：白色＋浅蓝色。侧边导航、组合概览、环境表现分布图、信息提示、持仓表，偏分析工作台。
2. **Sage green**：白色＋浅绿色。顶部导航、组合环形图、引导式首页、公司卡片、持仓表，偏普通投资者体验。

共用数据与行为，布局不是只换颜色。界面以英文展示，便于团队英文路演；此文档使用中文。

## 可以演示的流程

1. 切换两个设计版本。
2. 搜索公司、行业或市场；按持仓比例或环境评分降序排序。
3. 点击公司、图上的气泡或图例，打开详情；展开依据说明；Esc 关闭并回到原入口。
4. 进入 Explore changes，修改持仓比例。总和必须为 100%，不能为负数、空值或超过 100%。
5. 点击 Load example，再 Compare allocation，查看原始和草稿比例对比。继续编辑会清除旧对比；Reset 恢复原始值。
6. 查看 Our methodology，理解 E_score、E_weight、g 和资料局限。
7. 页脚 Demo state 可切换部分数据、加载、空组合和服务错误；错误后可以重试。
8. Export sample 下载实际展示的模拟数据 JSON。

## 文档对应关系

- 团队提供的 `Main Idea.docx`（原文档未包含在此源码仓库）：面向零售投资者、公司和组合层面、市场构想、模块化数据展示及前后端分离。
- 团队提供的 `escore_report.md`（原文档未包含在此源码仓库）：区分 E_score、E_weight、持仓比例和 greenness；展示 Carbon、Walk、Talk；缺失不按零分处理。
- 上一轮 `ui-spec.md`：概览 → 详情 → 调整对比，静态回退、异常状态、模拟数据标识。

资料里的预期收益优化和环境冲击模拟仍是研究与后端需求。本 Demo 不伪造收益、完整 ESG 评级或优化结果。

## 数据边界

- 五家公司、代码和全部指标均为虚构；市场标签用于布局演示，不表示已获得这些市场的数据。
- 数据文件：`src/data.ts`。它是展示模型，不是已经确认的后端 API。
- 四家公司有 E_score，合计原组合权重 88%；第五家公司没有分析。覆盖率不代表环境质量。
- E_score 为独立模拟值，不声称由演示的 Carbon/Walk/Talk 数值按研究报告算出。
- 公司 g 按提供的公式从模拟 E_score 和 E_weight 计算；不汇总成组合风险或预期收益。
- 比例对比在本地计算；原始组合不变。草稿在页面切换或刷新后重置，不保存到外部系统。
- 没有连接后端或 Lovable，没有部署、交易和账户注册。源码已上传至 Pachin1919/esg-investment-ui。

## 动画与同事接手

| 位置 | 当前实现 | 可扩展位置 |
| --- | --- | --- |
| 页面进入 | 320ms 淡入、7px 位移 | `.enter` / `reveal` |
| 公司详情 | 240ms 右侧进入 | `Modal` / `panel-in` |
| 公司卡片 | 悬停轻微上移 | `.company-story` |
| 对比图 | 400ms 宽度过渡；数据立即到位 | `.compare-track i` |
| 证据展开 | 200ms 淡入 | `.evidence` |
| 加载 | 900ms 本地样例准备；无虚构百分比 | `StateView` |

支持 `prefers-reduced-motion`；不使用滚动数字伪装实时计算。没有后台等待或预测计算。视频/复杂入口动画可后续独立加入，不应阻塞分析操作。

## 技术和交接

React + TypeScript + Vite，普通 CSS；Phosphor 图标，本地打包 DM Sans / Manrope 字体。

- `src/App.tsx`：两个布局和交互组件。
- `src/data.ts`：模拟公司数据、能力开关、覆盖率函数。
- `src/styles.css`：两套配色、布局、响应式和动效。

```powershell
npm run build
npm run preview
```

后端接入时增加 adapter，把实际字段转换为展示模型；只有返回和定义都明确的能力才开启。不要让 Lovable 和 Codex 同时修改同一页面。以实际连接的同步仓库为准，当前源码仓库为 Pachin1919/esg-investment-ui；这不代表已建立 Lovable 双向同步。

## 验证记录

- TypeScript 检查与 Vite 生产构建。
- 浏览器检查：筛选、缺失状态、详情与焦点恢复、导出、空/错误/加载恢复、双版本切换、减少动态效果。
- 比例检查：非法总和、负数、空输入被阻止；合法样例可比较；修改清除旧对比；基准可恢复。
- 桌面 1440px、手机 390px 截图检查；表格在自身区域内横向滚动。
- 首页预览图位于 `docs/previews/`；调试截图及自动化记录未提交。浏览器检查不等同于用户最终视觉验收。
