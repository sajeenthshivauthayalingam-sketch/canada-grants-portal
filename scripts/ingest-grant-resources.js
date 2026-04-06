// ingest-grant-resources.js
// Node 18+
// npm install csv-parse

import { parse } from "csv-parse/sync";
import fs from "node:fs/promises";

const INPUT_FILE = "./grant-datasets.json";
const MAX_RESOURCES_PER_DATASET = 3;

function pickBestResources(resources) {
  const preferredOrder = ["JSON", "CSV", "XLSX", "XLS", "XML", "ZIP"];
  return [...resources]
    .sort((a, b) => {
      const ai = preferredOrder.indexOf((a.format || "").toUpperCase());
      const bi = preferredOrder.indexOf((b.format || "").toUpperCase());
      return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
    })
    .slice(0, MAX_RESOURCES_PER_DATASET);
}

function normalizeRecord(record, source) {
  const keys = Object.keys(record);
  const lower = Object.fromEntries(
    keys.map((k) => [k.toLowerCase().trim(), record[k]])
  );

  const pick = (...names) => {
    for (const n of names) {
      const val = lower[n];
      if (val !== undefined && val !== null && String(val).trim() !== "") {
        return String(val).trim();
      }
    }
    return null;
  };

  return {
    source_dataset: source.title,
    source_organization: source.organization,
    source_url: source.resourceUrl,
    raw: record,

    grant_name: pick(
      "grant_name",
      "program_name",
      "program",
      "title",
      "opportunity_name",
      "funding_program"
    ),
    organization: pick(
      "organization",
      "department",
      "agency",
      "ministry",
      "owner_org",
      "sponsor"
    ) || source.organization || null,
    category: pick(
      "category",
      "subject",
      "theme",
      "type",
      "program_type"
    ),
    amount: pick(
      "amount",
      "funding_amount",
      "award_amount",
      "value",
      "total_value"
    ),
    deadline: pick(
      "deadline",
      "application_deadline",
      "close_date",
      "closing_date",
      "end_date"
    ),
    eligibility: pick(
      "eligibility",
      "eligibility_criteria",
      "applicant_type",
      "eligible_applicants"
    ),
    link: pick(
      "link",
      "url",
      "application_url",
      "program_url"
    ) || source.resourceUrl,
    status: pick(
      "status",
      "state",
      "opportunity_status"
    ),
  };
}

async function fetchText(url) {
  const res = await fetch(url, {
    headers: {
      Accept: "*/*",
      "User-Agent": "canada-grants-portal-research/1.0",
    },
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status} for ${url}`);
  }

  return res.text();
}

async function fetchJson(url) {
  const res = await fetch(url, {
    headers: {
      Accept: "application/json",
      "User-Agent": "canada-grants-portal-research/1.0",
    },
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status} for ${url}`);
  }

  return res.json();
}

async function loadRecordsFromResource(resource, dataset) {
  const format = String(resource.format || "").toUpperCase();
  const source = {
    title: dataset.title,
    organization: dataset.organization,
    resourceUrl: resource.url,
  };

  if (format === "CSV") {
    const text = await fetchText(resource.url);
    const rows = parse(text, {
      columns: true,
      skip_empty_lines: true,
      relax_column_count: true,
    });
    return rows.map((r) => normalizeRecord(r, source));
  }

  if (format === "JSON") {
    const json = await fetchJson(resource.url);

    if (Array.isArray(json)) {
      return json.map((r) => normalizeRecord(r, source));
    }

    if (Array.isArray(json.results)) {
      return json.results.map((r) => normalizeRecord(r, source));
    }

    if (Array.isArray(json.data)) {
      return json.data.map((r) => normalizeRecord(r, source));
    }

    return [normalizeRecord(json, source)];
  }

  return [];
}

async function main() {
  const raw = await fs.readFile(INPUT_FILE, "utf8");
  const payload = JSON.parse(raw);

  const all = [];

  for (const dataset of payload.datasets) {
    const resources = pickBestResources(dataset.resources);

    for (const resource of resources) {
      try {
        const records = await loadRecordsFromResource(resource, dataset);
        all.push(...records);
      } catch (err) {
        console.warn(`Skipping ${resource.url}: ${err.message}`);
      }
    }
  }

  await fs.writeFile("./normalized-grants.json", JSON.stringify(all, null, 2));
  console.log(`Wrote ${all.length} normalized records to normalized-grants.json`);
}

main();
