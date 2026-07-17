# 预定利率研究值模型

这是一个用于跟踪和展示“预定利率研究值”模型测算结果的 GitHub Pages 项目。

项目逻辑：

```text
公开市场数据
  ↓
GitHub Actions 自动抓取与计算
  ↓
生成 data/model-data.json 与 data/model-data.js
  ↓
index.html 展示交互看板
```

## 核心公式

```text
模型测算研究值
= MIN(负债端利率锚, 基础回报水平)
```

```text
负债端利率锚
= MA6(5年期以上LPR + 六大行5年定存均值) / 2
```

```text
基础回报水平
= MIN(MA250(10年期政策性金融债到期收益率),
      MA750(10年期政策性金融债到期收益率))
```

本项目不计算、不展示、不反推调节系数。页面结果为“模型测算研究值”，用于市场利率跟踪与情景研究，不代表对协会最终公布值或监管政策的机械预测。

## 政策性金融债口径

网页支持四种政策性金融债代表口径：

- 国开债
- 农发行债
- 进出口行债
- 三者均值

## 数据文件

| 文件 | 作用 |
| --- | --- |
| `data/model-data.json` | 结构化模型数据 |
| `data/model-data.js` | 网页直接加载的数据 |
| `data/deposit-rate-events.json` | 六大行 5 年定存维护表 |
| `data/lpr-events.json` | 5 年期以上 LPR 维护表 |
| `data/actual-reference-values.json` | 协会实际研究值维护表 |
| `scripts/update_model_data.py` | 自动抓取中债曲线并计算模型结果 |

## GitHub Pages

仓库设置中请确认：

```text
Settings -> Actions -> General -> Workflow permissions -> Read and write permissions
Settings -> Pages -> Build and deployment -> Source -> GitHub Actions
```

首次上传后，可以在 Actions 页面手动运行一次“更新预定利率研究值数据并部署”。
