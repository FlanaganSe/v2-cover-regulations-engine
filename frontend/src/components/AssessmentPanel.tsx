/** Assessment display panel for a selected parcel — card-based metric layout. */

import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  ExternalLink,
  FileText,
  Home,
  Info,
  MapPin,
  Shield,
} from "lucide-react";
import type { ParcelDetail } from "../types/assessment";
import { ConfidenceBadge } from "./ConfidenceBadge";

/** Only allow http/https URLs in href attributes. */
function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}

interface AssessmentPanelProps {
  detail: ParcelDetail;
}

function Divider(): React.JSX.Element {
  return <hr className="border-border-subtle" />;
}

function SectionHeader({
  icon,
  title,
  badge,
}: {
  icon: React.ReactNode;
  title: string;
  badge?: React.ReactNode;
}): React.JSX.Element {
  return (
    <div className="flex items-center justify-between">
      <h3 className="flex items-center gap-1.5 text-sm font-semibold text-text-primary">
        {icon}
        {title}
      </h3>
      {badge}
    </div>
  );
}

function SectionLabel({
  children,
}: {
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <p className="text-[11px] font-semibold tracking-widest text-text-muted uppercase">
      {children}
    </p>
  );
}

function MetricCard({
  value,
  label,
}: {
  value: string;
  label: string;
}): React.JSX.Element {
  return (
    <div className="rounded-md bg-bg-muted px-3 py-2">
      <div className="text-lg font-bold text-text-primary">{value}</div>
      <div className="text-[11px] text-text-muted">{label}</div>
    </div>
  );
}

function KeyValueRow({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}): React.JSX.Element | null {
  if (value == null) return null;
  return (
    <div className="flex items-baseline justify-between border-b border-border-subtle py-1.5 last:border-0">
      <span className="text-xs text-text-muted">{label}</span>
      <span className="text-right text-xs font-medium text-text-primary">
        {String(value)}
      </span>
    </div>
  );
}

/* ── Scope Warning ── */

function ScopeWarning({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element | null {
  const { scope } = detail;

  if (!scope.in_la_city) {
    return (
      <div className="rounded-lg border border-confidence-low/30 bg-confidence-low-bg p-3">
        <div className="flex items-center gap-2 text-sm font-medium text-confidence-low">
          <AlertTriangle className="h-4 w-4" />
          Out of scope — different jurisdiction
        </div>
        <p className="mt-1 text-xs text-confidence-low/80">
          This parcel is not within LA City limits. Regulations from a different
          jurisdiction apply.
        </p>
      </div>
    );
  }

  if (scope.chapter_1a) {
    return (
      <div className="rounded-lg border border-confidence-medium/30 bg-confidence-medium-bg p-3">
        <div className="flex items-center gap-2 text-sm font-medium text-confidence-medium">
          <AlertTriangle className="h-4 w-4" />
          Downtown (Chapter 1A) — not yet supported
        </div>
        <p className="mt-1 text-xs text-confidence-medium/80">
          This parcel is in a Chapter 1A zone. Development standards for
          downtown zones are not yet included in this tool.
        </p>
      </div>
    );
  }

  if (!scope.supported_zone) {
    return (
      <div className="rounded-lg border border-confidence-medium/30 bg-confidence-medium-bg p-3">
        <div className="flex items-center gap-2 text-sm font-medium text-confidence-medium">
          <AlertTriangle className="h-4 w-4" />
          Zone not in curated rule set
        </div>
        <p className="mt-1 text-xs text-confidence-medium/80">
          This zone is not yet supported. Standards shown may be incomplete.
          Review manually with LADBS.
        </p>
      </div>
    );
  }

  return null;
}

/* ── Summary ── */

function SummarySection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element {
  const { assessment } = detail;
  return (
    <section className="space-y-2">
      <SectionHeader
        icon={<FileText className="h-4 w-4 text-text-muted" />}
        title="Summary"
        badge={
          <span className="text-xs font-medium text-accent-primary">
            {assessment.llm_available ? "AI-generated" : "Automated"}
          </span>
        }
      />
      <p className="text-[13px] leading-relaxed text-text-secondary">
        {assessment.summary}
      </p>
    </section>
  );
}

/* ── Parcel Facts ── */

function ParcelFactsSection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element {
  const { parcel } = detail;
  return (
    <section className="space-y-2">
      <SectionHeader
        icon={<MapPin className="h-4 w-4 text-text-muted" />}
        title="Parcel"
      />
      <div>
        <KeyValueRow label="Address" value={parcel.address} />
        <KeyValueRow label="APN" value={parcel.apn ?? parcel.ain} />
        <KeyValueRow
          label="Lot size"
          value={
            parcel.lot_sqft ? `${parcel.lot_sqft.toLocaleString()} sqft` : null
          }
        />
        <KeyValueRow label="Year built" value={parcel.year_built} />
        <KeyValueRow label="Use" value={parcel.use_description} />
        <KeyValueRow label="Bedrooms" value={parcel.bedrooms} />
        <KeyValueRow
          label="Main sqft"
          value={parcel.sqft_main ? parcel.sqft_main.toLocaleString() : null}
        />
      </div>
    </section>
  );
}

/* ── Zoning & Standards ── */

function ZoningSection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element {
  const { zoning, standards } = detail;

  const flags = [
    zoning.q_flag && "Q (Qualified)",
    zoning.d_flag && "D (Development)",
    zoning.t_flag && "T (Tentative)",
  ].filter(Boolean) as string[];

  return (
    <section className="space-y-3">
      <SectionHeader
        icon={<Building2 className="h-4 w-4 text-text-muted" />}
        title="Zoning & Standards"
      />

      {/* Zone badge */}
      {zoning.zone_string && (
        <div>
          <span className="text-xs text-text-muted">Zone</span>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="rounded-md border border-border-default bg-bg-card px-2 py-1 text-xs font-semibold text-text-primary">
              {zoning.zone_string}
            </span>
            {flags.map((flag) => (
              <span
                key={flag}
                className="rounded bg-confidence-medium-bg px-1.5 py-0.5 text-[10px] font-semibold text-confidence-medium"
              >
                {flag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Zone details */}
      <div>
        <KeyValueRow label="Zone class" value={zoning.zone_class} />
        <KeyValueRow label="Height district" value={zoning.height_district} />
      </div>

      {/* 2x2 metric grid */}
      <div className="grid grid-cols-2 gap-2">
        <MetricCard
          value={
            standards.height_ft != null ? `${standards.height_ft} ft` : "—"
          }
          label="Max height"
        />
        <MetricCard
          value={
            standards.stories != null ? String(standards.stories) : "No limit"
          }
          label="Max stories"
        />
        <MetricCard
          value={
            standards.far_or_rfa != null ? String(standards.far_or_rfa) : "—"
          }
          label={standards.far_type ?? "FAR"}
        />
        <MetricCard
          value={standards.density_description ?? "—"}
          label="Density"
        />
      </div>

      {/* Setbacks */}
      {(standards.front_setback_ft != null ||
        standards.side_setback_ft != null ||
        standards.rear_setback_ft != null) && (
        <div className="space-y-2">
          <SectionLabel>Setbacks</SectionLabel>
          <div className="grid grid-cols-3 gap-2">
            {standards.front_setback_ft != null && (
              <MetricCard value={standards.front_setback_ft} label="Front" />
            )}
            {standards.side_setback_ft != null && (
              <MetricCard value={standards.side_setback_ft} label="Side" />
            )}
            {standards.rear_setback_ft != null && (
              <MetricCard value={standards.rear_setback_ft} label="Rear" />
            )}
          </div>
        </div>
      )}

      {/* Allowed uses */}
      {standards.allowed_uses.length > 0 && (
        <div className="space-y-1.5">
          <SectionLabel>Allowed uses</SectionLabel>
          <div className="flex flex-wrap gap-1.5">
            {standards.allowed_uses.map((use) => (
              <span
                key={use}
                className="rounded-md border border-border-default bg-bg-card px-2 py-0.5 text-xs text-text-secondary"
              >
                {use}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Suffixes */}
      {zoning.suffixes.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">Suffixes</span>
          <div className="flex gap-1">
            {zoning.suffixes.map((suffix) => (
              <span
                key={suffix}
                className="rounded bg-accent-primary-light px-1.5 py-0.5 text-[10px] font-semibold text-accent-primary"
              >
                {suffix}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

/* ── Overlays ── */

function OverlaysSection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element | null {
  const { overlays } = detail;
  const hasOverlays =
    overlays.specific_plan != null ||
    overlays.hpoz != null ||
    overlays.community_plan != null ||
    overlays.general_plan_lu != null;
  if (!hasOverlays) return null;

  return (
    <>
      <Divider />
      <section className="space-y-2">
        <SectionHeader
          icon={<Shield className="h-4 w-4 text-text-muted" />}
          title="Overlays"
        />
        {overlays.specific_plan && (
          <div className="rounded-md border border-overlay-sp/30 bg-overlay-sp-bg p-2.5 text-sm">
            <div className="font-medium text-overlay-sp">
              Specific Plan: {overlays.specific_plan.name}
            </div>
            {overlays.specific_plan.url &&
              isSafeUrl(overlays.specific_plan.url) && (
                <a
                  href={overlays.specific_plan.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-0.5 inline-flex items-center gap-1 text-xs text-overlay-sp hover:underline"
                >
                  View document <ExternalLink className="h-3 w-3" />
                </a>
              )}
            <p className="mt-0.5 text-xs text-overlay-sp/80">
              Additional restrictions may apply. Review the specific plan
              document.
            </p>
          </div>
        )}
        {overlays.hpoz && (
          <div className="rounded-md border border-overlay-hpoz/30 bg-overlay-hpoz-bg p-2.5 text-sm">
            <div className="font-medium text-overlay-hpoz">
              HPOZ: {overlays.hpoz.name}
            </div>
            {overlays.hpoz.url && isSafeUrl(overlays.hpoz.url) && (
              <a
                href={overlays.hpoz.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-0.5 inline-flex items-center gap-1 text-xs text-overlay-hpoz hover:underline"
              >
                View document <ExternalLink className="h-3 w-3" />
              </a>
            )}
            <p className="mt-0.5 text-xs text-overlay-hpoz/80">
              Historic preservation requirements apply. Consult HPOZ board
              before modifications.
            </p>
          </div>
        )}
        <KeyValueRow label="Community plan" value={overlays.community_plan} />
        <KeyValueRow label="General plan LU" value={overlays.general_plan_lu} />
      </section>
    </>
  );
}

/* ── ADU ── */

function AduSection({ detail }: { detail: ParcelDetail }): React.JSX.Element {
  const { adu } = detail;
  return (
    <section className="space-y-2">
      <SectionHeader
        icon={<Home className="h-4 w-4 text-text-muted" />}
        title="ADU Eligibility"
        badge={
          <span
            className={`text-xs font-semibold ${adu.allowed ? "text-confidence-high" : "text-confidence-low"}`}
          >
            {adu.allowed ? "Likely allowed" : "Not eligible"}
          </span>
        }
      />
      {adu.allowed && (
        <div className="grid grid-cols-2 gap-2">
          <MetricCard value={adu.max_sqft.toLocaleString()} label="Max sqft" />
          <MetricCard value={`${adu.setbacks_ft} ft`} label="Setbacks" />
        </div>
      )}
      {adu.notes && <p className="text-xs text-text-muted">{adu.notes}</p>}
    </section>
  );
}

/* ── Confidence ── */

function ConfidenceSection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element {
  const { confidence } = detail;
  return (
    <section className="space-y-2">
      <SectionHeader
        icon={<Shield className="h-4 w-4 text-text-muted" />}
        title="Confidence"
        badge={<ConfidenceBadge level={confidence.level} />}
      />
      {confidence.reasons.length > 0 && (
        <ul className="space-y-1">
          {confidence.reasons.map((reason, i) => (
            <li
              key={i}
              className="flex items-start gap-1.5 text-xs text-text-secondary"
            >
              <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-confidence-high" />
              {reason}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ── Citations ── */

function CitationsSection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element | null {
  const { assessment } = detail;
  if (assessment.citations.length === 0) return null;

  return (
    <section className="space-y-1.5">
      <SectionLabel>Citations</SectionLabel>
      <ul className="space-y-0.5 text-xs">
        {assessment.citations.map((citation, i) => (
          <li key={i}>
            {citation.startsWith("http") && isSafeUrl(citation) ? (
              <a
                href={citation}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-accent-primary hover:underline"
              >
                {citation.length > 60
                  ? citation.slice(0, 57) + "..."
                  : citation}
                <ExternalLink className="h-3 w-3" />
              </a>
            ) : (
              <span className="text-text-secondary">{citation}</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

/* ── Caveats ── */

function CaveatsSection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element | null {
  const { assessment } = detail;
  if (assessment.caveats.length === 0) return null;

  return (
    <div className="rounded-md border border-border-default bg-bg-muted p-3">
      <div className="flex items-center gap-1.5 text-xs font-medium text-text-muted">
        <Info className="h-3.5 w-3.5" />
        Disclaimers
      </div>
      <ul className="mt-1 space-y-1 text-xs text-text-secondary">
        {assessment.caveats.map((caveat, i) => (
          <li key={i}>{caveat}</li>
        ))}
      </ul>
    </div>
  );
}

/* ── Metadata Footer ── */

function MetadataFooter({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element | null {
  const { metadata } = detail;
  if (!metadata.data_as_of && metadata.source_urls.length === 0) return null;

  return (
    <div className="flex items-center justify-between text-xs text-text-tertiary">
      {metadata.data_as_of && (
        <span>
          Data as of{" "}
          {new Date(metadata.data_as_of).toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </span>
      )}
      <div className="flex gap-2">
        {metadata.source_urls.filter(isSafeUrl).map((url) => (
          <a
            key={url}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-0.5 text-accent-primary hover:underline"
          >
            View sources <ExternalLink className="h-3 w-3" />
          </a>
        ))}
      </div>
    </div>
  );
}

/* ── Main Panel ── */

export function AssessmentPanel({
  detail,
}: AssessmentPanelProps): React.JSX.Element {
  return (
    <div className="space-y-5">
      <ScopeWarning detail={detail} />
      <SummarySection detail={detail} />
      <Divider />
      <ParcelFactsSection detail={detail} />
      <Divider />
      <ZoningSection detail={detail} />
      <Divider />
      <OverlaysSection detail={detail} />
      <AduSection detail={detail} />
      <Divider />
      <ConfidenceSection detail={detail} />
      {(detail.assessment.citations.length > 0 ||
        detail.assessment.caveats.length > 0) && <Divider />}
      <CitationsSection detail={detail} />
      <CaveatsSection detail={detail} />
      <MetadataFooter detail={detail} />
    </div>
  );
}
