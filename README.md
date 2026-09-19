# Design MD Builder Skill

[English Version Below](#english-version)

此儲存庫包含一個專門的 AI Skill，旨在將 `design-tokens.json` 檔案（W3C DTCG / Design Token Builder 匯出格式）與設計參考資料轉換為符合 Google Stitch 規範的 `DESIGN.md` 以及包含單一檔案的 `preview.html` 預覽頁面。

## 總覽 (Overview)

這個 Skill 的核心原則是：**數據轉換交由腳本處理，設計判斷交由 AI 負責。**
手動轉換數百個 token 數值很容易出錯，因此提供的腳本會負責決定性的數值映射、對比度計算與格式驗證。AI 的任務則是閱讀參考資料、理解設計系統的意圖，並撰寫出精確的規則，讓其他模型在不看原始參考資料的情況下也能重現該設計。

## 產出物 (Deliverables)

此 Skill 會產生兩個確切的產出物：

1. **`DESIGN.md`**：作為其他 AI 工具（如 Stitch）在生成網頁、簡報、圖片與社群圖卡時所遵循的單一事實來源 (Single Source of Truth)。它包含了 YAML Frontmatter（機器可讀的 token）以及 Markdown 區塊（人類/AI 可讀的設計規則）。
2. **`preview.html`**：一個獨立的 HTML 頁面，會渲染所有的 token 並呈現一個逼真的 UI 範例畫面。讓使用者能在實際開始設計工作之前，預先檢視這套設計系統。

## 儲存庫結構 (Repository Structure)

- `SKILL.md`：給 AI 代理的主要指令說明檔，詳細說明了精確的工作流程、限制與格式化規則。
- `scripts/`：
  - `tokens_to_frontmatter.py`：將 DTCG token 轉換為 `frontmatter.yaml`、`extras.json` 以及分析報告 `report.md`。
  - `lint_design_md.py`：根據規範和內部規則（如對比度、token 引用是否正確）驗證生成的 `DESIGN.md`。
  - `build_preview.py`：使用 `DESIGN.md`、`extras.json` 與 UI 範例片段來建立 `preview.html`。
  - `colorlib.py`：計算顏色與對比度的共用工具。
- `references/`：
  - `spec.md`：Stitch `DESIGN.md` 的 Schema 規範。
  - `mapping-rules.md`：詳細說明 token 如何映射以及如何正確覆寫的規則。
  - `examples.md`：Stitch 風格原型與參考訊號決策指南。
- `assets/`：
  - `preview-template.html`：用於生成預覽頁面的 HTML 樣板。

## AI 工作流程 (AI Workflow)

當 AI 代理使用此 Skill 時，會遵循以下結構化流程：

1. **盤點輸入 (Inventory Inputs)**：尋找 `design-tokens.json` 以及任何參考資料（圖片、URL、程式碼、品牌指南）。
2. **轉換 Tokens (Convert Tokens)**：執行 `tokens_to_frontmatter.py` 來生成基礎的 YAML，並在報告中分析潛在問題。
3. **分析參考資料 (Analyze References)**：從提供的參考資料中擷取品牌個性、排版密度、影像風格與動態提示，以填補 token 無法表達的設計缺口。
4. **組裝 DESIGN.md (Assemble DESIGN.md)**：將生成的 frontmatter 與詳盡的 markdown 區塊（如 Brand & Style、Colors、Typography、Layout、Components 等）結合。
5. **程式碼檢查 (Lint)**：執行 `lint_design_md.py` 確保檔案結構正確，且符合所有無障礙設計及 Schema 的限制。
6. **建立預覽 (Build Preview)**：撰寫一個逼真且符合領域的 UI 範例片段，並執行 `build_preview.py` 生成互動式的預覽頁面。
7. **交付 (Deliver)**：向使用者呈現最終的 `DESIGN.md` 與 `preview.html`，並附上一份簡明的摘要報告。

## 使用方式 (Intended Use)

此儲存庫設計作為 AI Skill 來使用。具備執行腳本能力的 AI 助理可以閱讀 `SKILL.md` 並執行此目錄內的腳本，以自動化設計系統生成中的繁重工作，同時運用其專業的設計判斷力。

---

<a id="english-version"></a>
# English Version

This repository contains a specialized AI skill designed to convert a `design-tokens.json` file (W3C DTCG / Design Token Builder export) along with design references into a Google Stitch-compliant `DESIGN.md` and a single-file `preview.html`.

## Overview

The core principle of this skill is: **numbers come from scripts, judgment comes from the AI.**
Converting hundreds of token values by hand is prone to errors, so the provided scripts handle deterministic mapping, contrast math, and validation. The AI's job is to read the references, understand the design system's intent, and write precise rules that another model can reproduce without seeing the original references.

## Deliverables

This skill produces exactly two deliverables:

1. **`DESIGN.md`**: The single source of truth for other AI tools (like Stitch) to follow when generating web pages, slides, images, and social cards. It contains YAML frontmatter (machine-readable tokens) and Markdown sections (human/AI-readable design rules).
2. **`preview.html`**: A self-contained HTML page that renders every token alongside a realistic sample screen. This allows users to review the design system before actual implementation begins.

## Repository Structure

- `SKILL.md`: The main instruction file for the AI agent, detailing the exact workflow, constraints, and formatting rules.
- `scripts/`:
  - `tokens_to_frontmatter.py`: Converts DTCG tokens into `frontmatter.yaml`, `extras.json`, and an analysis `report.md`.
  - `lint_design_md.py`: Validates the generated `DESIGN.md` against spec and house rules (e.g., contrast ratios, token references).
  - `build_preview.py`: Builds the `preview.html` using the `DESIGN.md`, `extras.json`, and a sample HTML fragment.
  - `colorlib.py`: Shared utilities for color and contrast calculations.
- `references/`:
  - `spec.md`: The Stitch `DESIGN.md` schema specification.
  - `mapping-rules.md`: Rules detailing how tokens are mapped and how to properly override them.
  - `examples.md`: Stitch style archetypes and reference-signal decision guidelines.
- `assets/`:
  - `preview-template.html`: The HTML shell used for generating the preview page.

## AI Workflow

When an AI agent uses this skill, it follows a structured pipeline:

1. **Inventory Inputs**: Locate `design-tokens.json` and any reference materials (images, URLs, code, brand guidelines).
2. **Convert Tokens**: Run `tokens_to_frontmatter.py` to generate the base YAML and analyze potential issues in a report.
3. **Analyze References**: Extract brand personality, layout density, imagery styles, and motion cues from the provided references to fill gaps that tokens cannot express.
4. **Assemble DESIGN.md**: Combine the generated frontmatter with comprehensive markdown sections (Brand & Style, Colors, Typography, Layout, Components, etc.).
5. **Lint**: Run `lint_design_md.py` to ensure the file is structurally sound and meets all accessibility and schema constraints.
6. **Build Preview**: Write a realistic, domain-specific sample UI fragment and run `build_preview.py` to generate the interactive preview.
7. **Deliver**: Present the final `DESIGN.md` and `preview.html` to the user along with a concise summary report.

## Intended Use

This repository is designed to be consumed as an AI skill. An AI assistant with script execution capabilities can read `SKILL.md` and run the scripts within this directory to automate the heavy lifting of design system generation while applying expert design judgment.
