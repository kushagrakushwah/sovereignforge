import {
  Cube,
  Eye,
  FileDoc,
  FileXls,
  MagnifyingGlass,
  PresentationChart,
  Scan,
  TerminalWindow,
  TextAlignLeft,
  Tray,
  type Icon,
} from "@phosphor-icons/react";

const ICONS: Record<string, Icon> = {
  ocr: Scan,
  extract: TextAlignLeft,
  draft_word: FileDoc,
  draft_ppt: PresentationChart,
  draft_excel: FileXls,
  code_sandbox: TerminalWindow,
  image_understand: Eye,
  search_kb: MagnifyingGlass,
  ingest_file: Tray,
};

export function ToolIcon({ tool, className }: { tool: string; className?: string }) {
  const Glyph = ICONS[tool] ?? Cube;
  return <Glyph weight="light" className={className} />;
}
