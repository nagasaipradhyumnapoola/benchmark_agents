import Link from "next/link";
import { ArrowUpRight, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageTitle } from "@/components/common";

const sections = [
  ["publish", "What you can publish"],
  ["safe-use", "Importing and running agents"],
  ["results", "Honest benchmark results"],
  ["community", "Community conduct"],
  ["privacy", "Your data and credentials"],
  ["report", "Report a problem"],
] as const;

export default function Page() {
  return (
    <div className="rules-page">
      <PageTitle
        title="Rules & safety"
        description="Know what you share. Understand what you run."
        action={
          <Button asChild variant="outline">
            <Link href="/hub">
              Explore agents <ArrowUpRight size={14} />
            </Link>
          </Button>
        }
      />
      <div className="rules-intro">
        <ShieldCheck size={23} strokeWidth={1.5} aria-hidden="true" />
        <p>
          Publishing makes your source available to everyone using the connected
          registry. Importing brings someone else’s code into your workspace.
          These are separate decisions.
        </p>
      </div>
      <div className="rules-layout">
        <nav aria-label="Rules sections" className="rules-index">
          {sections.map(([id, title]) => (
            <a key={id} href={`#${id}`}>
              {title}
            </a>
          ))}
          <p>
            Publication rules
            <br />
            <span>Version 2026-10-23</span>
          </p>
        </nav>
        <article className="rules-content">
          <section id="publish">
            <h2>What you can publish</h2>
            <p>
              Share agents you created or have permission to distribute. Include
              the source, an accurate license, a useful README, a version and
              the model requirements.
            </p>
            <ul>
              <li>
                Keep passwords, API keys, private keys, personal data and
                private configuration out of every file, argument and
                description.
              </li>
              <li>
                Do not publish malware, credential theft, hidden data
                collection, destructive behavior or deceptive claims about what
                an agent does.
              </li>
              <li>
                Explain network access, dependencies, costs and limitations.
                Recommended models are suggestions; validate each pairing before
                relying on it.
              </li>
              <li>
                Published versions are immutable. Publish a new version for
                changes. A source digest identifies content; it does not certify
                that code is safe.
              </li>
            </ul>
            <p>
              Each publication requires acknowledgement of the current rules.
              The registry records the account, release, rules version and time.
              This is an attestation, not a security review.
            </p>
          </section>
          <section id="safe-use">
            <h2>Importing and running agents</h2>
            <p>
              Read the source and license before importing. Import stages a
              specific release and registers it locally; it does not execute the
              code or install dependencies.
            </p>
            <ul>
              <li>
                Run third-party code in an isolated environment. Host agents
                have your application’s operating-system privileges.
              </li>
              <li>
                Review dependencies separately. A fresh task folder is not a
                sandbox.
              </li>
              <li>
                Connect your own authorized local model or hosted endpoint.
                Hosted requests may incur provider charges.
              </li>
              <li>
                Execution needs both the server setting and your experiment
                authorization. Compatibility does not prove trustworthiness.
              </li>
            </ul>
            <Link href="/docs#agent-hub" className="subtle-link">
              Read the integration guide <ArrowUpRight size={14} />
            </Link>
          </section>
          <section id="results">
            <h2>Honest benchmark results</h2>
            <p>
              Report the model, benchmark, source version and conditions that
              produced the result. Keep failures and limitations visible.
            </p>
            <ul>
              <li>
                Hub contributions are self-reported. The registry has not
                independently run or verified them.
              </li>
              <li>
                Do not present deterministic demonstrations as real-model
                capability measurements.
              </li>
              <li>
                Do not invent scores, hide failures or imply that a small public
                task set establishes a universal ranking.
              </li>
              <li>
                Review exported evidence for private data before sharing. A
                completed job can contain failed task checks.
              </li>
            </ul>
          </section>
          <section id="community">
            <h2>Community conduct</h2>
            <p>
              Discuss the work respectfully. Give useful reproduction steps and
              credit the people whose source you use.
            </p>
            <ul>
              <li>
                No harassment, impersonation, spam, deceptive listings or
                manipulated recommendations.
              </li>
              <li>
                Do not post someone else’s private information or credentials.
              </li>
              <li>
                Use public issues for ordinary bugs and suggestions. Use a
                private channel for vulnerabilities or sensitive evidence.
              </li>
            </ul>
            <p>
              This development registry does not yet provide a staffed
              moderation service, automated takedowns or account recovery.
              Operators must establish those services before opening
              registration widely.
            </p>
          </section>
          <section id="privacy">
            <h2>Your data and credentials</h2>
            <p>
              Model connections, private execution and local evidence stay in
              the Lab. The shared registry stores accounts, published source,
              comments, publication acknowledgements and contributed summaries.
            </p>
            <ul>
              <li>
                Session keys are held in the running process and need re-entry
                after restart. Environment references store a variable name
                instead of its value.
              </li>
              <li>
                A hosted model receives the prompts you choose to send. Review
                its provider’s data policy separately.
              </li>
              <li>
                Publishing sends selected source and metadata to the connected
                registry. Sharing a completed run sends its summary, not an API
                key or raw private traces.
              </li>
              <li>
                Credential masking is best effort. It cannot guarantee removal
                of every unknown secret or personal detail.
              </li>
            </ul>
            <p>
              Self-hosted operators are responsible for access policies,
              retention, backups, deletion requests and their deployment’s
              privacy notice. This describes the software, not a hosted-service
              privacy contract.
            </p>
          </section>
          <section id="report">
            <h2>Report a problem</h2>
            <p>
              For ordinary bugs, unsafe listings or licensing concerns, include
              the public agent slug, version, digest and a concise description.
              Leave credentials and private evidence out of public reports.
            </p>
            <div className="rules-report-links">
              <a
                className="subtle-link"
                href="https://github.com/nagasaipradhyumnapoola/benchmark_agents/issues/new/choose"
                target="_blank"
                rel="noopener noreferrer"
              >
                Report a public issue <ArrowUpRight size={14} />
              </a>
              <a
                className="subtle-link"
                href="https://github.com/nagasaipradhyumnapoola/benchmark_agents/security"
                target="_blank"
                rel="noopener noreferrer"
              >
                Security reporting options <ArrowUpRight size={14} />
              </a>
            </div>
            <p>
              Check the Security tab for a private reporting option. If
              unavailable, request a private maintainer contact without posting
              exploit details or secrets. Revoke or rotate an accidentally
              published key immediately and contact the registry operator. No
              response-time or automatic removal guarantee is offered.
            </p>
          </section>
        </article>
      </div>
    </div>
  );
}
