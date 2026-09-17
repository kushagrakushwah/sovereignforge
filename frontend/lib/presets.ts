export interface Preset {
  title: string;
  pipeline: string;
  prompt: string;
}

export const PRESETS: Preset[] = [
  {
    title: "Approval note",
    pipeline: "Document → Word",
    prompt:
      "Read the uploaded inspection report, extract all findings and risks, then draft an approval note as a Word document",
  },
  {
    title: "Board deck",
    pipeline: "Document → Slides",
    prompt:
      "Read the uploaded inspection report and create a board-ready PowerPoint presentation with findings, risk matrix, and recommendations",
  },
  {
    title: "Risk register",
    pipeline: "Document → Workbook",
    prompt:
      "Analyze the uploaded inspection report and generate an Excel risk register with action plan and severity classifications",
  },
  {
    title: "P&ID review",
    pipeline: "Vision",
    prompt:
      "Analyze this P&ID diagram and identify all instrument tags, safety valves, and potential hazard points",
  },
  {
    title: "Standards-backed pack",
    pipeline: "Document + Knowledge → Word, Slides",
    prompt:
      "Read the inspection report, search the knowledge base for relevant standards, draft Word approval note AND a PPT summary",
  },
  {
    title: "Wall thickness check",
    pipeline: "Code sandbox",
    prompt:
      "Calculate the minimum pipe wall thickness for a 6-inch crude oil line at 24 bar using ASME B31.3, run in sandbox and show results",
  },
  {
    title: "Earthing limits",
    pipeline: "Knowledge search",
    prompt:
      "Search the knowledge base for earthing resistance standards and acceptable limits per OISD and IS:3043",
  },
];
