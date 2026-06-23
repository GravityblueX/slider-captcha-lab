from __future__ import annotations

import json
import tkinter as tk
from html import escape
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

class ReportCenter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('留痕 - 综合报告中心')
        self.geometry('1080x740')
        self.files = []
        self._build()

    def _build(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        title = ttk.Label(root, text='综合测试报告中心', font=('Microsoft YaHei UI', 18, 'bold'))
        title.pack(anchor='w')
        ttk.Label(root, text='导入行为会话、授权滑块测试、风险分析、环境体检等 JSON，生成统一 HTML 报告。').pack(anchor='w', pady=(4, 10))

        bar = ttk.Frame(root)
        bar.pack(fill=tk.X, pady=6)
        ttk.Button(bar, text='添加 JSON 文件', command=self.add_files).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text='移除选中', command=self.remove_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text='清空', command=self.clear).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text='生成 HTML 报告', command=self.export_html).pack(side=tk.RIGHT, padx=4)

        self.tree = ttk.Treeview(root, columns=('path','type','summary'), show='headings', height=14)
        for col, name, width in [('path','文件',520),('type','识别类型',160),('summary','摘要',340)]:
            self.tree.heading(col, text=name)
            self.tree.column(col, width=width, anchor='w')
        self.tree.pack(fill=tk.X, pady=8)

        self.preview = tk.Text(root, wrap=tk.WORD)
        self.preview.pack(fill=tk.BOTH, expand=True, pady=8)

        ttk.Label(root, text='提示：各工具导出的 JSON 都可以加入；报告中心会尽量自动识别结构并汇总。', foreground='#555').pack(anchor='w')

    def add_files(self):
        paths = filedialog.askopenfilenames(filetypes=[('JSON','*.json'),('All','*.*')])
        for p in paths:
            try:
                data = json.loads(Path(p).read_text(encoding='utf-8'))
                typ, summary = self.identify(data)
                item = {'path': p, 'type': typ, 'summary': summary, 'data': data}
                self.files.append(item)
                self.tree.insert('', tk.END, values=(p, typ, summary))
            except Exception as e:
                messagebox.showerror('导入失败', f'{p}\n{e}')
        self.refresh_preview()

    def identify(self, data):
        if 'fingerprint' in data and ('events' in data or 'risks' in str(data)[:1000]):
            fp = data.get('fingerprint', {})
            return '风险分析', f"环境评分: {fp.get('score','-')} / 100"
        if 'logs' in data and 'summary' in data and data.get('scope'):
            s = data.get('summary', {})
            return '行为会话', f"动作: {s.get('total','-')} 成功: {s.get('ok','-')} 失败: {s.get('failed','-')}"
        if 'results' in data and 'summary' in data:
            s = data.get('summary', {})
            return '授权滑块测试', f"总数: {s.get('total','-')} 通过: {s.get('passed','-')} 失败: {s.get('failed','-')}"
        if 'modules' in data and 'playwright_chromium' in data:
            return '环境体检', f"评分: {data.get('score','-')} 结论: {data.get('verdict','-')}"
        if data.get('report_type') == 'cdp_diagnostics':
            page = data.get('page', {})
            cdp = data.get('cdp', {})
            session = data.get('browser_session', {})
            mode = '真实Chrome' if session.get('attached_to_existing_chrome') else '托管Chromium'
            return 'CDP授权诊断', f"{mode} frames: {page.get('frame_count','-')} targets: {cdp.get('target_count','-')}"
        if 'frames' in data and data.get('browser_session') and data.get('scope'):
            summary = data.get('summary', {})
            session = data.get('browser_session', {})
            mode = '真实Chrome' if session.get('attached_to_existing_chrome') else '托管Chromium'
            best_count = len(summary.get('best_candidates', []) or [])
            return '页面结构探测', f"{mode} frames: {summary.get('frame_count','-')} candidates: {summary.get('visible_candidate_count','-')} best: {best_count}"
        if 'score' in data and 'verdict' in data:
            return '单项评分', f"评分: {data.get('score')} 结论: {data.get('verdict')}"
        return '未知 JSON', '已导入，无法自动识别摘要'

    def remove_selected(self):
        sels = list(self.tree.selection())
        for sel in reversed(sels):
            idx = self.tree.index(sel)
            self.tree.delete(sel)
            if 0 <= idx < len(self.files):
                self.files.pop(idx)
        self.refresh_preview()

    def clear(self):
        self.files.clear()
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.refresh_preview()

    def refresh_preview(self):
        self.preview.delete('1.0', tk.END)
        self.preview.insert(tk.END, '当前报告素材：\n\n')
        for i, f in enumerate(self.files, 1):
            self.preview.insert(tk.END, f"{i}. [{f['type']}] {f['summary']}\n   {f['path']}\n")

    def export_html(self):
        if not self.files:
            messagebox.showwarning('没有素材', '请先添加 JSON 文件。')
            return
        path = filedialog.asksaveasfilename(defaultextension='.html', filetypes=[('HTML','*.html')])
        if not path:
            return
        Path(path).write_text(self.make_html(), encoding='utf-8')
        messagebox.showinfo('完成', f'已导出综合报告：{path}')

    def make_html(self):
        cards = []
        for f in self.files:
            data = escape(json.dumps(f['data'], ensure_ascii=False, indent=2))
            insight = self.render_insight(f['data'])
            cards.append(f"""
<section class='card'>
  <h2>{escape(f['type'])}</h2>
  <p><b>文件：</b>{escape(f['path'])}</p>
  <p><b>摘要：</b>{escape(f['summary'])}</p>
  {insight}
  <details><summary>查看原始 JSON</summary><pre>{data}</pre></details>
</section>
""")
        return f"""<!doctype html><html><head><meta charset='utf-8'><title>留痕综合测试报告</title>
<style>body{{font-family:system-ui,'Microsoft YaHei',sans-serif;background:#f6f7fb;margin:0;padding:28px}}h1{{margin-top:0}}.card{{background:white;border:1px solid #e5e7eb;border-radius:14px;padding:18px;margin:14px 0;box-shadow:0 8px 24px #0000000d}}pre{{background:#111827;color:#d1fae5;padding:14px;border-radius:10px;overflow:auto}}.note{{color:#666}}</style></head><body>
<h1>留痕综合测试报告</h1>
<p class='note'>本报告由留痕工具生成，用于本地、自有或明确授权范围内的行为模拟、环境检查与测试结果归档。</p>
{''.join(cards)}
<h2>结论说明</h2>
<p>请结合授权范围、测试目标、页面流程、账号/IP/Session/Token 等服务端因素综合判断。本报告不代表可通过任何真实网站风控。</p>
</body></html>"""

    def render_insight(self, data):
        if 'frames' in data and data.get('summary', {}).get('best_candidates'):
            rows = []
            for item in data.get('summary', {}).get('best_candidates', [])[:8]:
                rows.append(
                    "<tr>"
                    f"<td>{escape(str(item.get('frame_index', '-')))}</td>"
                    f"<td>{escape(str(item.get('score', '-')))}</td>"
                    f"<td><code>{escape(str(item.get('selector', '')))}</code></td>"
                    f"<td>{escape(', '.join(item.get('reasons', []) or []))}</td>"
                    "</tr>"
                )
            return (
                "<h3>候选控件线索</h3>"
                "<table><thead><tr><th>Frame</th><th>Score</th><th>Selector</th><th>Reasons</th></tr></thead>"
                f"<tbody>{''.join(rows)}</tbody></table>"
            )
        return ''

if __name__ == '__main__':
    ReportCenter().mainloop()
