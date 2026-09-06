"use client";

import { useEffect, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  ChevronRight,
  Clock3,
  Headphones,
  LayoutDashboard,
  Menu,
  Mic2,
  Phone,
  PhoneCall,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
  UserSearch,
  X,
  Zap,
} from "lucide-react";
import { api } from "./api";
import { PeopleSearchForm } from "./PeopleSearchForm";
import type { Call, Candidate } from "./types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type Page =
  | "Overview"
  | "People search"
  | "Outreach"
  | "Conversations"
  | "Attendance plan";
const nav: [Page, typeof LayoutDashboard][] = [
  ["Overview", LayoutDashboard],
  ["People search", UserSearch],
  ["Outreach", PhoneCall],
  ["Conversations", Headphones],
  ["Attendance plan", ShieldCheck],
];
function Pill({
  children,
  tone = "gray",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <Badge className={tone}>{children}</Badge>;
}
const display = (value: unknown): string =>
  value == null
    ? "Not provided"
    : typeof value === "object"
      ? JSON.stringify(value)
      : String(value);

function resultPreview(result: Call["result"]) {
  const summary = result.summary ?? result.qualification_summary;
  if (typeof summary === "string" && summary.trim()) return summary;
  return (
    Object.entries(result)
      .slice(0, 3)
      .map(([key, value]) => `${key.replaceAll("_", " ")}: ${display(value)}`)
      .join("; ") || "No answers yet"
  );
}

export default function App() {
  const [page, setPage] = useState<Page>("Overview");
  const [data, setData] = useState<Awaited<
    ReturnType<typeof api.dashboard>
  > | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
  const [sourced, setSourced] = useState<Candidate[]>([]);
  const [contactSource, setContactSource] = useState<"account" | "search">(
    "account",
  );
  const [company, setCompany] = useState("");
  const [contactPage, setContactPage] = useState(0);
  const [callPage, setCallPage] = useState(0);
  const [activeId, setActiveId] = useState("");
  const pageSize = 20;
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [page]);
  useEffect(() => {
    setContactPage(0);
  }, [query]);
  useEffect(() => {
    if (page === "Conversations" && activeId) {
      document
        .getElementById("call-detail")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [page, activeId]);
  const [selected, setSelected] = useState<string[]>([]);
  const [agent, setAgent] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [detail, setDetail] = useState<Call | null>(null);
  const [detailError, setDetailError] = useState("");
  const [detailLoading, setDetailLoading] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  async function refresh(force = true) {
    setLoading(true);
    setError("");
    try {
      if (!force && !data) {
        const preview = await api.dashboardPreview();
        setData(preview);
        if (!preview.partial) {
          setAgent(preview.default_agent_id);
          return;
        }
      }
      const response = await api.dashboard(force);
      setData(response);
      setAgent((current) =>
        response.agents.some((a) => a.id === current)
          ? current
          : response.default_agent_id,
      );
      setSelected((current) =>
        current.filter(
          (id) =>
            id.startsWith("pdl-") ||
            response.candidates.some((c) => c.id === id),
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load Hunar data");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void refresh(false);
  }, []);
  useEffect(() => {
    if (!activeId) return;
    let cancelled = false;
    setDetail(null);
    setDetailError("");
    setDetailLoading(true);
    api
      .call(activeId)
      .then((call) => {
        if (!cancelled) setDetail(call);
      })
      .catch((e) => {
        if (!cancelled)
          setDetailError(
            e instanceof Error ? e.message : "Could not load call",
          );
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeId, data]);
  const candidates = [...sourced, ...(data?.candidates ?? [])];
  const calls = data?.calls ?? [];
  const filtered = candidates
    .filter((c) =>
      contactSource === "search" ? c.source === "pdl" : c.source !== "pdl",
    )
    .filter((c) =>
      `${c.name} ${c.role} ${c.company} ${c.location} ${c.phone} ${c.skills.join(" ")}`
        .toLowerCase()
        .includes(query.toLowerCase()),
    );
  const chosen = candidates.filter((c) => selected.includes(c.id));
  const completed = calls.filter(
    (c) => c.status.toUpperCase() === "COMPLETED",
  ).length;
  const interested = calls.filter((c) =>
    ["true", "yes", "high", "interested"].includes(
      String(c.result.interested ?? c.result.interest ?? "").toLowerCase(),
    ),
  ).length;
  async function launch() {
    setLaunching(true);
    setMessage("");
    try {
      const result = await api.outreach(selected, agent, confirmed, company);
      setMessage(result.message);
      setConfirmed(false);
      setSelected([]);
      setPage("Conversations");
      await refresh();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not launch outreach");
    } finally {
      setLaunching(false);
    }
  }
  function callRows(rows: Call[]) {
    return rows.length ? (
      <div className="table call-table">
        <div className="tr th">
          <span>Contact</span>
          <span>Status</span>
          <span>Result</span>
          <span>Duration</span>
          <span />
        </div>
        {rows.map((c) => (
          <div
            className={`tr ${activeId === c.id ? "active-call" : ""}`}
            key={c.id}
          >
            <b className="call-name" data-label="Contact">
              {c.candidate_name}
            </b>
            <span>
              <Pill>{c.status}</Pill>
            </span>
            <span
              data-label="Result"
              className="result-preview"
              title={resultPreview(c.result)}
            >
              {resultPreview(c.result)}
            </span>
            <span data-label="Duration">{c.duration} sec</span>
            <button
              className="icon"
              aria-label={`View call for ${c.candidate_name}`}
              onClick={() => {
                setActiveId(c.id);
                setPage("Conversations");
              }}
            >
              <ChevronRight />
            </button>
          </div>
        ))}
      </div>
    ) : (
      <div className="empty">No calls returned by Hunar.</div>
    );
  }
  return (
    <div className="app">
      <aside className={mobileNav ? "open" : ""}>
        <div className="brand-row">
          <div className="logo">
            <Zap /> Niyora
          </div>
          <button
            className="icon mobile-only"
            onClick={() => setMobileNav(false)}
            aria-label="Close navigation"
          >
            <X />
          </button>
        </div>
        <div className="workspace">
          <div className="workspace-icon">H</div>
          <div>
            <b>Hunar workspace</b>
            <small>Voice outreach</small>
          </div>
        </div>
        <nav>
          {nav.map(([label, Icon]) => (
            <button
              key={label}
              className={page === label ? "active" : ""}
              onClick={() => {
                setPage(label);
                setMobileNav(false);
              }}
            >
              <Icon size={18} />
              {label}
              {label === "Conversations" && data && <em>{calls.length}</em>}
            </button>
          ))}
        </nav>
        <div className="side-bottom">
          <p>
            {loading
              ? "Connecting to company account..."
              : data
                ? "Connected company account"
                : "Company connection unavailable"}
          </p>
        </div>
      </aside>
      {mobileNav && (
        <div className="scrim" onClick={() => setMobileNav(false)} />
      )}
      <main>
        <header>
          <button
            className="icon mobile-only"
            onClick={() => setMobileNav(true)}
            aria-label="Open navigation"
          >
            <Menu />
          </button>
          <div className="crumb">
            Hunar <ChevronRight size={14} />
            <b>{page}</b>
          </div>
          <div className="header-actions">
            <div className={`connection ${data && !loading ? "live" : ""}`}>
              <i />
              {loading
                ? data
                  ? "Updating..."
                  : "Loading Hunar..."
                : data
                  ? "Hunar connected"
                  : "Hunar unavailable"}
            </div>
            <Button
              onClick={() => void refresh()}
              disabled={loading || launching}
            >
              Refresh
            </Button>
          </div>
        </header>
        {data && (
          <nav className="workflow" aria-label="Hiring workflow">
            {(["People search", "Outreach", "Conversations"] as Page[]).map(
              (step, index) => (
                <button
                  key={step}
                  aria-current={page === step ? "step" : undefined}
                  onClick={() => setPage(step)}
                >
                  <span>{index + 1}</span>
                  {
                    ["Select contacts", "Set up outreach", "Review answers"][
                      index
                    ]
                  }
                  <ChevronRight size={15} />
                </button>
              ),
            )}
          </nav>
        )}
        {message && (
          <div
            className="card"
            role="status"
            style={{ margin: 24, padding: 20 }}
          >
            {message}
          </div>
        )}
        {data?.partial && (
          <div className="card" role="status" style={{ margin: 24, padding: 20 }}>
            Showing the first batch of company records. Counts are partial.
            {loading ? " Loading remaining records..." : " Use Retry to load all records."}
          </div>
        )}
        {error && (
          <div
            className="card"
            role="alert"
            style={{ margin: 24, padding: 20 }}
          >
            <h3>
              {data
                ? "Could not refresh company data"
                : "Could not load company data"}
            </h3>
            {data && <p>Showing the last successfully loaded data.</p>}
            <p>{error}</p>
            <Button onClick={() => void refresh()}>Retry</Button>
          </div>
        )}
        {page === "Attendance plan" ? (
          <Attendance />
        ) : loading && !data ? (
          <div className="empty" role="status">
            Loading company data from Hunar...
          </div>
        ) : (
          data && (
            <>
              {page === "Overview" && (
                <div className="page">
                  <div className="welcome">
                    <div>
                      <Pill tone="lime">Hunar account</Pill>
                      <h1>Your outreach overview.</h1>
                      <p>
                        Metrics calculated from the calls returned by your
                        company account.
                      </p>
                    </div>
                    <Button onClick={() => setPage("People search")}>
                      View contacts
                    </Button>
                  </div>
                  <section className="metrics">
                    {[
                      ["Contacts", candidates.length],
                      ["Calls completed", completed],
                      ["Interested responses", interested],
                      ["Agents", data.agents.length],
                    ].map(([label, value]) => (
                      <article key={label}>
                        <div>
                          <small>{label}</small>
                          <strong>{value}</strong>
                        </div>
                      </article>
                    ))}
                  </section>
                  <section className="card calls-card">
                    <div className="card-head">
                      <h2>Recent calls</h2>
                      <Button onClick={() => setPage("Conversations")}>
                        View all {calls.length} calls
                      </Button>
                    </div>
                    {callRows(
                      [...calls]
                        .sort((a, b) =>
                          b.created_at.localeCompare(a.created_at),
                        )
                        .slice(0, 10),
                    )}
                  </section>
                  <section
                    className="card"
                    style={{ marginTop: 24, padding: 24 }}
                  >
                    <h2>Company agents</h2>
                    {data.agents.length ? (
                      <div className="agent-list">
                        {data.agents.map((a) => (
                          <div key={a.id} style={{ marginTop: 16 }}>
                            <b>{a.name}</b> <Pill>{a.status}</Pill>
                            <p>{a.summary}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p>No agents returned by Hunar.</p>
                    )}
                  </section>
                </div>
              )}
              {page === "People search" && (
                <div className="page search-page">
                  <div className="title-row">
                    <div>
                      <span className="eyebrow">HUNAR CONTACTS</span>
                      <h1>People in your company account.</h1>
                      <p>
                        Contacts from Hunar call history. Search the details
                        supplied by Hunar.
                      </p>
                    </div>
                  </div>
                  <PeopleSearchForm
                    onResults={(rows) => {
                      setSourced(rows);
                      setContactSource("search");
                      setContactPage(0);
                      setQuery("");
                      setSelected((current) =>
                        current.filter((id) => !id.startsWith("pdl-")),
                      );
                    }}
                  />
                  <div
                    className="sourcing-actions"
                    style={{ marginBottom: 20 }}
                  >
                    <Button
                      onClick={() => {
                        setContactSource("account");
                        setContactPage(0);
                      }}
                      aria-pressed={contactSource === "account"}
                    >
                      Existing account contacts
                    </Button>
                    <Button
                      onClick={() => {
                        setContactSource("search");
                        setContactPage(0);
                      }}
                      aria-pressed={contactSource === "search"}
                    >
                      Search results ({sourced.length})
                    </Button>
                  </div>
                  <section className="search-builder card">
                    <label>
                      Search name, phone, role, company or skills
                      <div className="input">
                        <Search size={16} />
                        <input
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                          placeholder="Search Hunar contacts"
                        />
                      </div>
                    </label>
                  </section>
                  <div className="results-head">
                    <h2>{filtered.length} contacts</h2>
                    <Button
                      disabled={!chosen.length}
                      onClick={() => setPage("Outreach")}
                    >
                      Reach out to {chosen.length}
                    </Button>
                  </div>
                  <div className="candidate-list">
                    {filtered
                      .slice(
                        contactPage * pageSize,
                        (contactPage + 1) * pageSize,
                      )
                      .map((c) => (
                        <article
                          className={`candidate card ${selected.includes(c.id) ? "selected" : ""}`}
                          key={c.id}
                        >
                          <input
                            aria-label={`Select ${c.name}`}
                            type="checkbox"
                            disabled={!c.phone}
                            checked={selected.includes(c.id)}
                            onChange={(e) =>
                              setSelected(
                                e.target.checked
                                  ? [...selected, c.id]
                                  : selected.filter((id) => id !== c.id),
                              )
                            }
                          />
                          <span className="avatar large">{c.avatar}</span>
                          <div className="candidate-main">
                            <div>
                              <h3>{c.name}</h3>
                              <Pill>{c.status}</Pill>
                              {c.source === "pdl" && (
                                <Pill>People Data Labs</Pill>
                              )}
                            </div>
                            <b>
                              {c.role || "Role not provided"}
                              {c.company && ` at ${c.company}`}
                            </b>
                            <p>
                              {c.phone || "Phone not provided"}
                              {c.location && ` | ${c.location}`}
                            </p>
                            <div className="skills">
                              {c.skills.map((skill, i) => (
                                <Pill key={`${skill}-${i}`}>{skill}</Pill>
                              ))}
                            </div>
                          </div>
                        </article>
                      ))}
                  </div>
                  {filtered.length > pageSize && (
                    <div className="pagination">
                      <Button
                        disabled={!contactPage}
                        onClick={() => setContactPage(contactPage - 1)}
                      >
                        Previous
                      </Button>
                      <span>
                        Page {contactPage + 1} of{" "}
                        {Math.ceil(filtered.length / pageSize)}
                      </span>
                      <Button
                        disabled={
                          (contactPage + 1) * pageSize >= filtered.length
                        }
                        onClick={() => setContactPage(contactPage + 1)}
                      >
                        Next
                      </Button>
                    </div>
                  )}
                  {!filtered.length && (
                    <div className="empty">
                      No contacts found in the Hunar data.
                    </div>
                  )}
                </div>
              )}
              {page === "Outreach" && (
                <div className="page">
                  <div className="title-row">
                    <div>
                      <h1>Launch Hunar voice outreach.</h1>
                      <p>
                        Calls use the selected agent's script and the contact
                        details stored in Hunar.
                      </p>
                    </div>
                  </div>
                  <section
                    className="card outreach-setup"
                    style={{ padding: 24 }}
                  >
                    <Button onClick={() => setPage("People search")}>
                      Edit selected contacts
                    </Button>
                    <h2>{chosen.length} selected contacts</h2>
                    {chosen.map((c) => (
                      <p key={c.id}>
                        {c.name} | {c.phone || "No phone"}
                      </p>
                    ))}
                    {!chosen.length && (
                      <Button onClick={() => setPage("People search")}>
                        Select contacts
                      </Button>
                    )}
                    <label style={{ display: "block", marginTop: 24 }}>
                      Hunar agent{" "}
                      <select
                        value={agent}
                        onChange={(e) => {
                          setAgent(e.target.value);
                          setConfirmed(false);
                        }}
                      >
                        <option value="">Select an agent</option>
                        {data.agents.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    {chosen.some((c) => c.source === "pdl") && (
                      <label className="hiring-company">
                        Hiring company
                        <input
                          value={company}
                          onChange={(e) => setCompany(e.target.value)}
                          maxLength={150}
                          placeholder="Company the agent is hiring for"
                        />
                      </label>
                    )}
                    {!data.live_calls && (
                      <p>
                        Live calling is disabled in the server configuration.
                      </p>
                    )}
                    <label style={{ display: "block", margin: "24px 0" }}>
                      <input
                        type="checkbox"
                        checked={confirmed}
                        onChange={(e) => setConfirmed(e.target.checked)}
                      />{" "}
                      Place real phone calls to these {chosen.length} contacts
                      using this agent.
                    </label>
                    <Button
                      disabled={
                        launching ||
                        !confirmed ||
                        !data.live_calls ||
                        !chosen.length ||
                        (chosen.some((c) => c.source === "pdl") &&
                          !company.trim()) ||
                        !data.agents.some((a) => a.id === agent)
                      }
                      onClick={launch}
                    >
                      {launching ? "Sending to Hunar..." : "Launch live calls"}
                    </Button>
                  </section>
                </div>
              )}
              {page === "Conversations" && (
                <div className="page">
                  <div className="title-row">
                    <div>
                      <h1>Company conversations.</h1>
                      <p>Statuses, recordings and answers from Hunar.</p>
                    </div>
                  </div>

                  {activeId && (
                    <section
                      id="call-detail"
                      className="card detail call-detail"
                      style={{ marginBottom: 24, padding: 24 }}
                    >
                      <div className="detail-toolbar">
                        <h2>Call details</h2>
                        <Button onClick={() => setActiveId("")}>
                          Close details
                        </Button>
                      </div>
                      {detailLoading ? (
                        <p>Loading call details...</p>
                      ) : detailError ? (
                        <p role="alert">{detailError}</p>
                      ) : (
                        detail && (
                          <>
                            <h2>{detail.candidate_name}</h2>
                            <Pill>{detail.status}</Pill>
                            <p>{detail.duration} seconds</p>
                            <h3>Structured answers</h3>
                            <div className="answer-grid">
                              {Object.entries(detail.result).map(([k, v]) => (
                                <div key={k}>
                                  <small>{k.replaceAll("_", " ")}</small>
                                  <b>{display(v)}</b>
                                </div>
                              ))}
                            </div>
                            {!Object.keys(detail.result).length && (
                              <p>
                                No structured answers supplied for this call.
                              </p>
                            )}
                            <h3>Recording</h3>
                            {/^https?:\/\//.test(detail.recording_url) ? (
                              <audio
                                controls
                                src={detail.recording_url}
                                preload="none"
                              />
                            ) : (
                              <p>No recording supplied for this call.</p>
                            )}
                            <h3>Transcript</h3>
                            {detail.transcript.length ? (
                              detail.transcript.map((t, i) => (
                                <div key={i}>
                                  <b>{t.speaker}</b>
                                  <p>{t.text}</p>
                                </div>
                              ))
                            ) : (
                              <p>No transcript supplied for this call.</p>
                            )}
                          </>
                        )
                      )}
                    </section>
                  )}
                  <section className="card calls-card">
                    <div className="card-head">
                      <h2>All conversations</h2>
                      <span>{calls.length} calls</span>
                    </div>
                    {callRows(
                      [...calls]
                        .sort((a, b) =>
                          b.created_at.localeCompare(a.created_at),
                        )
                        .slice(callPage * pageSize, (callPage + 1) * pageSize),
                    )}
                    {calls.length > pageSize && (
                      <div className="pagination">
                        <Button
                          disabled={!callPage}
                          onClick={() => setCallPage(callPage - 1)}
                        >
                          Previous
                        </Button>
                        <span>
                          Page {callPage + 1} of{" "}
                          {Math.ceil(calls.length / pageSize)}
                        </span>
                        <Button
                          disabled={(callPage + 1) * pageSize >= calls.length}
                          onClick={() => setCallPage(callPage + 1)}
                        >
                          Next
                        </Button>
                      </div>
                    )}
                  </section>
                </div>
              )}
            </>
          )
        )}
      </main>
    </div>
  );
}

function Attendance() {
  const steps = [
    [
      "01",
      "Local IVR check-in",
      "Every location gets a dedicated phone number. Employees call from any feature phone or shared landline and enter their employee PIN.",
    ],
    [
      "02",
      "Voice biometric + location proof",
      "The AI asks a rotating spoken phrase, matches the enrolled voiceprint, and verifies the originating site number or supervisor kiosk.",
    ],
    [
      "03",
      "Offline-first site gateway",
      "A low-cost GSM/landline terminal stores encrypted events during outages and syncs them centrally when connectivity returns.",
    ],
    [
      "04",
      "Exception-only HR workflow",
      "LLM flags duplicate, late, missing, or suspicious entries and calls the employee or supervisor for clarification automatically.",
    ],
  ];
  return (
    <div className="page attendance">
      <div className="attendance-hero">
        <Pill tone="lime">
          <ShieldCheck size={13} /> Feature proposal: not live attendance data
        </Pill>
        <h1>
          Attendance without apps.
          <br />
          <em>Built for the real world.</em>
        </h1>
        <p>
          A voice-first, privacy-aware attendance system for 1,000 employees
          across 100 locations using feature phones, landlines, and an LLM
          coordination layer.
        </p>
        <div>
          <Pill>1,000 employees</Pill>
          <Pill>100 locations</Pill>
          <Pill>No smartphones</Pill>
          <Pill>Works offline</Pill>
        </div>
      </div>
      <section className="architecture card">
        <div className="card-head">
          <div>
            <span className="eyebrow">SYSTEM DESIGN</span>
            <h2>
              One simple action for employees.
              <br />
              Complete visibility for HR.
            </h2>
          </div>
        </div>
        <div className="flow">
          <div>
            <span>
              <Phone />
            </span>
            <b>Employee</b>
            <small>Feature phone / landline</small>
          </div>
          <ArrowRight />
          <div>
            <span>
              <Mic2 />
            </span>
            <b>Voice IVR</b>
            <small>PIN + voice phrase</small>
          </div>
          <ArrowRight />
          <div>
            <span>
              <ShieldCheck />
            </span>
            <b>Verification</b>
            <small>Identity + site proof</small>
          </div>
          <ArrowRight />
          <div>
            <span>
              <Sparkles />
            </span>
            <b>LLM layer</b>
            <small>Exceptions + follow-ups</small>
          </div>
          <ArrowRight />
          <div>
            <span>
              <BarChart3 />
            </span>
            <b>HR dashboard</b>
            <small>Live attendance view</small>
          </div>
        </div>
      </section>
      <section className="plan-grid">
        {steps.map(([n, t, d]) => (
          <article key={n} className="card">
            <span>{n}</span>
            <h3>{t}</h3>
            <p>{d}</p>
          </article>
        ))}
      </section>
      <section className="guardrails">
        <div>
          <ShieldCheck />
          <h2>Designed against buddy punching</h2>
          <p>
            Voiceprint liveness, one-time rotating phrases, site-bound caller
            IDs, anomaly scoring, and supervisor verification protect accuracy
            without turning attendance into surveillance.
          </p>
        </div>
        <div>
          <Clock3 />
          <h2>Graceful when systems fail</h2>
          <p>
            Each site has paper fallback codes generated daily. Supervisors SMS
            or call in the batch once lines recover; every correction remains
            visible in an immutable audit trail.
          </p>
        </div>
        <div>
          <Users />
          <h2>Human review stays in control</h2>
          <p>
            The LLM never changes payroll data on its own. It gathers context,
            assigns confidence, and routes exceptions to HR with the call
            evidence and a recommended action.
          </p>
        </div>
      </section>
    </div>
  );
}
