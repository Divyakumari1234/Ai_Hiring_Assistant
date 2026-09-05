"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "./api";
import type { Candidate } from "./types";

export function PeopleSearchForm({
  onResults,
}: {
  onResults: (rows: Candidate[]) => void;
}) {
  const [jd, setJd] = useState("");
  const [title, setTitle] = useState("");
  const [location, setLocation] = useState("");
  const [skills, setSkills] = useState("");
  const [limit, setLimit] = useState(5);
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    api
      .searchConfig()
      .then((r) => setConfigured(r.configured))
      .catch(() => setConfigured(null));
  }, []);
  const payload = () => ({
    job_description: jd,
    job_title: title,
    location,
    skills: skills
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    limit,
  });
  async function run(search: boolean) {
    setBusy(true);
    setMessage("");
    try {
      if (search) {
        const result = await api.search(payload());
        onResults(result.results);
        setMessage(
          `${result.results.length} profiles returned from People Data Labs (${result.total} total matches). Missing phone numbers cannot be used for calls.`,
        );
      } else {
        const filters = await api.searchCriteria(payload());
        setTitle(filters.job_title);
        setSkills(filters.skills.join(", "));
        setMessage(
          "Review the extracted title and skills before searching. Add location if needed.",
        );
      }
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="card sourcing-form">
      <h2>Find new candidates from a job description</h2>
      <p>
        People Data Labs supplies the profiles. Review contacts before using
        Hunar for outreach.
      </p>
      {configured === false && (
        <p role="status">
          Person Search is not connected yet. Configure the separate People Data
          Labs key on the server.
        </p>
      )}
      <label>
        Job description
        <textarea
          value={jd}
          maxLength={12000}
          rows={5}
          onChange={(e) => setJd(e.target.value)}
          placeholder="Paste the role, responsibilities and required skills"
        />
      </label>
      <div className="sourcing-fields">
        <label>
          Job title
          <input
            value={title}
            maxLength={120}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Software engineer"
          />
        </label>
        <label>
          Location
          <input
            value={location}
            maxLength={120}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Bengaluru, India"
          />
        </label>
        <label>
          Required skills, comma-separated
          <input
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            placeholder="Python, SQL"
          />
        </label>
        <label>
          Maximum profiles
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
          >
            {[1, 5, 10, 20].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p>
        Search uses your provider credits for returned profiles. Filters are
        editable; no match scores are invented.
      </p>
      <div className="sourcing-actions">
        <Button
          disabled={busy || jd.trim().length < 20}
          onClick={() => run(false)}
        >
          Read job description
        </Button>
        <Button
          disabled={busy || configured !== true || jd.trim().length < 20}
          onClick={() => run(true)}
        >
          {busy ? "Working..." : "Search new candidates"}
        </Button>
      </div>
      {message && <p role="status">{message}</p>}
    </section>
  );
}
