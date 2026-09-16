# 软著登记 + JOSS 投稿 操作清单（2026-09）

两件事互不冲突，材料高度复用。建议顺序：先打软著（周期长、材料现成），
同时准备 JOSS（等 Zenodo DOI 后提交）。

## 一、软件著作权登记（中国版权保护中心，CPCC）

登记免费、周期约 30-40 个工作日，全程网上：https://www.ccopyright.com.cn

需要准备的材料（本仓库已生成大半，见 `docs/copyright/`）：

| 材料 | 状态 | 说明 |
|---|---|---|
| 申请表 | 自己填报 | 网上填报系统生成 |
| 源程序文档 | ✅ `source_code_document.txt` | 前30页+后30页、每页50行、含页眉（软件名+版本+页码）；粘入 Word 按分页符分页后导出 PDF |
| 用户手册 | ✅ `user_manual_zh.md` 草稿 | 配截图定稿后转 PDF；程序操作截图建议现截 |
| 身份证明 | 自己准备 | 个人：身份证复印件；署名与手册一致 |

填报关键字段（自己定夺）：
- 软件全称：建议 `D3LTool NASA卫星数据下载软件`（全称需与文档一致）
- 版本号：`V2.0.2`
- 开发完成日期：自己定（建议填本次发布日期或稍早）
- 首次发表日期：GitHub Release 公开之日（2026-09）或填"未发表"
- 著作权人：戴劭勍（个人）
- 开发的硬件环境/软件环境：按 `README.md` 与手册"运行环境"填
- 编程语言：Python

注意：
- 软著登记不审查代码来源，AI 辅助开发不影响登记；
- 软著登记与后续 MIT 开源不冲突（登记的是既有版本的权利归属）；
- 软著名称与 GitHub 仓库名无需一致，但文档内部必须统一。

## 二、JOSS 投稿（Journal of Open Source Software）

投稿入口：https://joss.theoj.org/submit（OpenReview 平台）

已完成（仓库内）：
- ✅ `paper/paper.md` —— 投稿短文草稿（英文，JOSS 结构），提交前删除草稿注释、补 Zenodo DOI
- ✅ `CITATION.cff` —— 引用元数据（含 ORCID 0000-0003-0858-4728）
- ✅ 41 项 pytest + GitHub Actions CI + 中英文档 + MIT 许可

待办（按序）：
1. **Zenodo 归档拿 DOI**：
   - 登录 zenodo.org，授权 GitHub 账号，把 `GISerDaiShaoqing/D3LTool` 仓库打开托管；
   - 对应 release（用 `v2.0.3`（已含产品目录等最新功能））会被自动抓取成 Zenodo 版本，
     把"版本 DOI"（不是概念 DOI）填进 `paper/paper.md` 头部；
2. **补 affiliation**：paper.md 作者行现在是"Independent researcher"，若挂单位请改成单位名；
3. **终校 paper.md**：字数（正文 250-1000 词已达标）、删掉给作者看的注释；
4. 提交后正常 3-6 周内得到初审意见，审稿人可能要求补充测试或文档说明。

## 三、两件事的时间安排

- 软著：材料现在就可以提交，等结果期间办 JOSS；
- JOSS：打下一个 tag（v2.0.3+）触发 CI 构建后，在 Zenodo 关联仓库拿 DOI，即可提交。
