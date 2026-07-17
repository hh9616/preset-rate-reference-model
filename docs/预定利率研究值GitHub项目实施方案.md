# 预定利率研究值 GitHub 网页项目实施方案

更新日期：2026-07-17

## 1. 项目定位

本项目拟在 GitHub 上搭建一个可自动更新、可交互展示的“预定利率研究值”研究网页，形式参考已经跑通的利率曲线展示项目：

```text
公开数据源
  ↓
GitHub Actions 定时抓取与计算
  ↓
生成 JSON / JS 数据文件
  ↓
GitHub Pages 展示交互网页
```

页面展示的是“模型测算研究值”，用于研究市场利率变化与预定利率研究值之间的关系，不应表述为对中国保险行业协会最终公布值的机械预测。

本阶段不引入、不反推调节系数。若未来确需研究调节系数，应作为单独模块，并在页面上明确标注为情景假设。

## 2. 核心逻辑结论

本项目的核心任务，是把预定利率研究值拆成“负债端利率锚”和“资产端基础回报”两部分，并用公开市场利率数据持续跟踪。

当前模型所需的数据结构为：

| 字段 | 说明 |
| --- | --- |
| 日期 | 交易日序列，覆盖 2020 年首个工作日至最新可获取日期 |
| 六大行 5 年定期存款利率 | 工、农、中、建、邮储、交行 5 年定期存款利率报价 |
| 5 年期以上 LPR | 负债端利率输入 |
| 六大行 5 年定期存款利率均值 | 六家银行 5 年定存报价的算术平均 |
| 10 年期国债到期收益率 | 税收溢价测算参考 |
| 10 年期国开债到期收益率 | 政策性金融债代表口径之一 |
| 10 年期农发行债到期收益率 | 政策性金融债代表口径之一 |
| 10 年期进出口行债到期收益率 | 政策性金融债代表口径之一 |
| 10 年期政策性金融债三者均值 | 国开债、农发行债、进出口行债 10 年到期收益率的算术平均 |
| 负债端利率锚 | `(5年期以上LPR + 六大行5年定存均值) 6个月移动平均 / 2` |
| 基础回报水平 | 政策性金融债 10 年到期收益率的 250 日移动平均与 750 日移动平均取低 |
| 模型测算研究值 | `MIN(负债端利率锚, 基础回报水平)` |
| 协会实际研究值 | 中国保险行业协会公布的实际研究值，用于对照 |

当前页面应维护的协会实际研究值为：

| 时间 | 实际研究值 |
| --- | --- |
| 2025Q1 | 2.34% |
| 2025Q2 | 2.13% |
| 2025Q3 | 1.99% |
| 2025Q4 | 1.90% |
| 2026Q1 | 1.89% |
| 2026Q2 | 1.93% |

网页项目应以上表作为当前维护表，并保留季度末日期映射逻辑。

## 3. 模型公式口径

### 3.1 官方公式表达

根据公开口径，预定利率研究值由下述公式确定：

```text
模型测算研究值
= MIN(负债端利率锚, 基础回报水平)
```

其中：

```text
负债端利率锚
= MA6(5年期以上LPR + 六大行5年定期存款利率均值) / 2
```

定期存款利率为六大国有银行 5 年定期存款利率报价均值。

### 3.2 基础回报水平

基础回报水平的研究公式为：

```text
基础回报水平
= MIN(MA250(10年期国债到期收益率 + 税收溢价),
      MA750(10年期国债到期收益率 + 税收溢价))
```

国债与政策性金融债收益率差异主要由于国债利息收入免税，二者息差可作为税收溢价的代表：

```text
税收溢价
≈ 10年期政策性金融债到期收益率 - 10年期国债到期收益率
```

因此网页计算可等价使用：

```text
基础回报水平
= MIN(MA250(10年期政策性金融债到期收益率),
      MA750(10年期政策性金融债到期收益率))
```

### 3.3 政策性金融债代表口径

网页应支持政策性金融债代表口径切换：

```text
国开债
农发行债
进出口行债
三者均值
```

建议实现方式：

- 页面提供切换按钮，支持国开债、农发行债、进出口行债、三者均值；
- 每个口径都重新计算 MA250、MA750、基础回报水平和最终模型测算研究值；
- 默认口径可在页面中配置，汇报时应明确当前采用的政策性金融债代表口径。

## 4. 数据源设计

### 4.1 需要抓取或维护的数据

| 数据 | 项目字段 | 频率 | 来源 | 自动化建议 |
| --- | --- | --- | --- | --- |
| 5 年期以上 LPR | `lpr5y` | 月度，向后填充到交易日 | 全国银行间同业拆借中心 / 中国货币网 | 自动抓取 |
| 工行 5 年定存 | `icbc5y` | 变更日，向后填充 | 银行官网或维护表 | 先维护，后自动化 |
| 农行 5 年定存 | `abc5y` | 变更日，向后填充 | 银行官网或维护表 | 先维护，后自动化 |
| 中行 5 年定存 | `boc5y` | 变更日，向后填充 | 银行官网 | 可优先自动核验 |
| 建行 5 年定存 | `ccb5y` | 变更日，向后填充 | 银行官网或维护表 | 先维护，后自动化 |
| 邮储 5 年定存 | `psbc5y` | 变更日，向后填充 | 银行官网或维护表 | 先维护，后自动化 |
| 交行 5 年定存 | `bocom5y` | 变更日，向后填充 | 银行官网或维护表 | 先维护，后自动化 |
| 国债 10 年到期收益率 | `gov10yYtm` | 交易日 | 中国债券信息网 | 自动抓取 |
| 国开债 10 年到期收益率 | `cdb10yYtm` | 交易日 | 中国债券信息网 | 自动抓取 |
| 农发行债 10 年到期收益率 | `adb10yYtm` | 交易日 | 中国债券信息网 | 自动抓取 |
| 进出口行债 10 年到期收益率 | `exim10yYtm` | 交易日 | 中国债券信息网 | 自动抓取 |
| 协会实际研究值 | `actualReferenceValue` | 季度 | 中国保险行业协会公告 | 手工维护，保留来源 |

### 4.2 中债收益率曲线接口

中债曲线使用已经验证过的公开接口：

```text
POST https://yield.chinabond.com.cn/cbweb-mn/yc/searchYc
```

关键参数：

| 参数 | 取值 |
| --- | --- |
| `workTimes` | `YYYY-MM-DD` |
| `qxll` | `0` 表示到期收益率，`1` 表示即期收益率 |
| `ycDefIds` | 曲线 ID |

本项目资产端使用到期收益率口径：

```text
qxll=0
```

曲线 ID：

| 曲线 | ycDefId | 期限 |
| --- | --- | --- |
| 国债 | `2c9081e50a2f9606010a3068cae70001` | 取 10Y |
| 国开债 | `8a8b2ca037a7ca910137bfaa94fa5057` | 取 10Y |
| 农发行债 | `2c9081e50a2f9606010a306abdde0003` | 取 10Y |
| 进出口行债 | `8a8b2ca0567e033b01567ea9c1d96af8` | 取 10Y |

`seriesData` 中直接包含整数期限点，例如 `[10.0, 1.8233]`，因此取 10Y 时无需插值，只需筛选：

```text
abs(tenor - 10.0) < 1e-6
```


## 5. 数据文件结构

建议仓库结构如下：

```text
preset-rate-reference-model/
  index.html
  README.md
  scripts/
    update_model_data.py
    fetch_chinabond.py
    fetch_lpr.py
    calc_model.py
  data/
    model-data.json
    model-data.js
    deposit-rate-events.json
    actual-reference-values.json
  docs/
    预定利率研究值GitHub项目实施方案.md
    数据源与口径说明.md
  .github/
    workflows/
      update-data.yml
```

### 5.1 `deposit-rate-events.json`

六大行定存建议用“事件表”维护，不建议每天手填。

```json
[
  {
    "date": "2025-05-20",
    "icbc5y": 1.30,
    "boc5y": 1.30,
    "abc5y": 1.30,
    "ccb5y": 1.30,
    "psbc5y": 1.30,
    "bocom5y": 1.30,
    "source": "manual",
    "note": "六大行五年期整存整取挂牌利率调整"
  }
]
```

脚本运行时将事件表向后填充到每个交易日，生成日度序列。

### 5.2 `actual-reference-values.json`

协会实际研究值建议单独维护，方便更新来源和备注。

```json
[
  {
    "quarter": "2025Q1",
    "asOfDate": "2024-12-31",
    "value": 2.34,
    "source": "中国保险行业协会",
    "note": "实际研究值"
  },
  {
    "quarter": "2025Q2",
    "asOfDate": "2025-03-31",
    "value": 2.13,
    "source": "中国保险行业协会",
    "note": "实际研究值"
  }
]
```

注意：JSON 中利率统一用百分数数值，例如 `2.34` 表示 `2.34%`，不要混用 `0.0234`。

### 5.3 `model-data.json`

主数据文件建议包含原始数据、计算结果和元信息：

```json
{
  "updatedAt": "2026-07-17T18:30:00+08:00",
  "unit": "percent",
  "calculationMode": "official_ma6",
  "policyBondMode": "cdb|adb|exim|mean",
  "series": [
    {
      "date": "2025-06-30",
      "icbc5y": 1.30,
      "boc5y": 1.30,
      "abc5y": 1.30,
      "ccb5y": 1.30,
      "psbc5y": 1.30,
      "bocom5y": 1.30,
      "deposit5yMean": 1.30,
      "lpr5y": 3.50,
      "gov10yYtm": 1.65,
      "cdb10yYtm": 1.78,
      "adb10yYtm": 1.78,
      "exim10yYtm": 1.77,
      "policy10yMean": 1.78,
      "liabilityAnchor": 2.5572,
      "assetBaseReturn": 2.0118,
      "modelReferenceValue": 2.0118,
      "actualReferenceValue": 1.99,
      "actualMinusModelBp": -2.18
    }
  ],
  "actualValues": [],
  "sources": {
    "chinabond": "https://yield.chinabond.com.cn/cbweb-mn/yc/searchYc",
    "lpr": "全国银行间同业拆借中心/中国货币网",
    "association": "中国保险行业协会"
  }
}
```

### 5.4 `model-data.js`

为了让本地双击 `index.html` 也能打开，可同时生成：

```js
window.MODEL_DATA = { ... };
```

网页优先加载 `data/model-data.js`，部署环境也可用 `fetch("data/model-data.json")`。

## 6. 计算脚本设计

建议核心脚本为：

```text
scripts/update_model_data.py
```

运行流程：

1. 读取已有 `data/model-data.json`，判断起始日期；
2. 抓取 LPR 历史数据；
3. 抓取中债国债、国开债、农发行债、进出口行债 10Y 到期收益率；
4. 读取 `deposit-rate-events.json`，向后填充六大行定存利率；
5. 生成统一日度数据表；
6. 计算：
   - 六大行定存均值；
   - 负债端利率锚；
   - 政策债 10Y 的 MA250、MA750；
   - 资产端基础回报；
   - 模型测算研究值；
   - 与协会实际研究值的偏差；
7. 写出 `model-data.json` 和 `model-data.js`；
8. 保留日志，说明哪些日期无中债数据、哪些字段由维护表填充。

核心函数建议：

```python
def moving_average(values, window):
    ...

def calc_deposit_mean(row):
    return mean([icbc5y, boc5y, abc5y, ccb5y, psbc5y, bocom5y])

def calc_liability_anchor(rows, idx, window="6M"):
    return (avg_lpr5y + avg_deposit5y_mean) / 2

def calc_asset_base_return(rows, idx, policy_key):
    ma250 = moving_average(policy_series, 250)
    ma750 = moving_average(policy_series, 750)
    return min(ma250, ma750)

def calc_model_reference_value(liability_anchor, asset_base_return):
    return min(liability_anchor, asset_base_return)
```

第一版应优先保证与官方公式口径一致：

```text
负债端窗口：6 个月移动平均
资产端窗口：250 个交易日和 750 个交易日
最终结果：不乘调节系数
```

## 7. 网页功能设计

网页第一屏不要做宣传页，直接展示研究看板。

建议页面分为五块：

### 7.1 顶部总览

展示最新日期下：

- 模型测算研究值；
- 协会实际研究值；
- 负债端利率锚；
- 资产端基础回报；
- 当前触发项：负债端约束 / 资产端约束；
- 实际值 - 模型值，单位 bp。

### 7.2 公式解释区

用简洁卡片展示：

```text
模型测算研究值 = MIN(负债端利率锚, 资产端基础回报)
负债端利率锚 = MA6(5年期以上LPR + 六大行5年定存均值) / 2
资产端基础回报 = MIN(MA250(政策债10Y), MA750(政策债10Y))
```

旁边标注：

```text
当前为模型测算口径；不含调节系数。
```

### 7.3 政策债口径切换

提供按钮：

```text
国开债
农发行债
进出口行债
三者均值
```

切换后重新计算资产端基础回报和模型测算研究值。

### 7.4 历史图表

至少包含两张图：

1. 模型结果对比图：
   - 模型测算研究值；
   - 协会实际研究值；
   - 负债端利率锚；
   - 资产端基础回报。

2. 利率输入图：
   - 5 年期以上 LPR；
   - 六大行 5 年定存均值；
   - 国债 10Y；
   - 国开债 10Y；
   - 农发行债 10Y；
   - 进出口行债 10Y；
   - 政策债三者均值。

图表支持：

- 时间范围切换：3 个月、6 个月、1 年、全部；
- 指标勾选；
- 鼠标悬停显示同日数值；
- CSV 导出。

### 7.5 历史校准表

按季度展示：

| 季度 | 基准日 | 协会实际研究值 | 模型测算研究值 | 负债端锚 | 资产端回报 | 实际-模型(bp) |
| --- | --- | --- | --- | --- | --- | --- |

该表用于汇报和回测，建议支持导出 CSV。

## 8. GitHub Actions 自动更新

工作流文件：

```text
.github/workflows/update-data.yml
```

建议流程：

```yaml
name: 更新预定利率研究值数据并部署

on:
  schedule:
    - cron: '45 10 * * 1-5'  # 北京时间 18:45
  workflow_dispatch:
  push:
    branches: [main]

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  update-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: 更新模型数据
        run: python scripts/update_model_data.py
      - name: 提交数据变化
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/model-data.json data/model-data.js data/deposit-rate-events.json data/actual-reference-values.json
          if git diff --cached --quiet; then
            echo "数据无变化"
          else
            git commit -m "自动更新预定利率研究值数据"
            git push
          fi
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
      - id: deployment
        uses: actions/deploy-pages@v4
```

需要在 GitHub 仓库中确认：

- `Settings -> Actions -> General -> Workflow permissions` 选择 `Read and write permissions`；
- `Settings -> Pages -> Build and deployment -> Source` 选择 `GitHub Actions`；
- 首次在 `Actions` 页面手动运行一次，确认数据文件和网页部署成功。

## 9. 第一版验收标准

第一版项目跑通后，应满足：

- GitHub Pages 能打开网页；
- GitHub Actions 可以手动运行成功；
- 网页展示最新数据日期；
- 10 年国债、国开债、农发行债、进出口行债到期收益率可自动更新；
- 六大行定存可以通过维护表更新并向后填充；
- 计算结果能复现核心公式口径；
- 协会实际研究值能在校准表中对照；
- 页面明确写出“模型测算研究值，不含调节系数”；
- 数据可以导出 CSV。

## 10. 后续增强方向

1. 补齐六大行五年定存历史变更表，减少手工维护误差。
2. 优化 6 个月移动平均的日度展开方式，并在页面中说明计算口径。
3. 加入“普通型产品预定利率上限 - 实际研究值”的观察列。
4. 加入情景分析：
   - LPR 上下调整；
   - 定存利率上下调整；
   - 政策债 10Y 上下调整；
   - 国开债、农发行债、进出口行债代表口径切换。
5. 增加数据质量检查：
   - 当天中债数据缺失；
   - 非交易日跳过；
   - LPR 或定存利率未更新；
   - MA250/MA750 数据不足。
6. 增加数据来源说明和免责声明，方便使用者打开 GitHub 后理解项目。

## 11. 对外说明建议

可在网页底部或 README 中使用以下表述：

```text
本项目依据公开信息，将预定利率研究值拆分为负债端利率锚和资产端基础回报两部分，参考 5 年期以上 LPR、六大国有银行 5 年期定存挂牌利率、10 年期国债及政策性金融债到期收益率等公开市场指标。模型结果用于跟踪市场利率变化、开展情景分析，并与中国保险行业协会公布的研究值进行对照；不代表对协会最终研究值或监管政策的机械预测。
```


