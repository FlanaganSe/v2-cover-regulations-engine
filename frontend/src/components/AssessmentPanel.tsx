/** Full assessment display panel for a selected parcel. */

import {
  AlertTriangle,
  Building2,
  ExternalLink,
  FileText,
  Home,
  Info,
  MapPin,
  Scale,
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

function SectionHeader({
  icon,
  title,
}: {
  icon: React.ReactNode;
  title: string;
}): React.JSX.Element {
  return (
    <h3 className="flex items-center gap-1.5 text-sm font-semibold text-gray-700">
      {icon}
      {title}
    </h3>
  );
}

function KeyValue({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}): React.JSX.Element | null {
  if (value == null) return null;
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">{String(value)}</span>
    </div>
  );
}

function ScopeWarning({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element | null {
  const { scope } = detail;

  if (!scope.in_la_city) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-3">
        <div className="flex items-center gap-2 text-sm font-medium text-red-800">
          <AlertTriangle className="h-4 w-4" />
          Out of scope — different jurisdiction
        </div>
        <p className="mt-1 text-xs text-red-700">
          This parcel is not within LA City limits. Regulations from a different
          jurisdiction apply.
        </p>
      </div>
    );
  }

  if (scope.chapter_1a) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
        <div className="flex items-center gap-2 text-sm font-medium text-amber-800">
          <AlertTriangle className="h-4 w-4" />
          Downtown (Chapter 1A) — not yet supported
        </div>
        <p className="mt-1 text-xs text-amber-700">
          This parcel is in a Chapter 1A zone. Development standards for
          downtown zones are not yet included in this tool.
        </p>
      </div>
    );
  }

  if (!scope.supported_zone) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
        <div className="flex items-center gap-2 text-sm font-medium text-amber-800">
          <AlertTriangle className="h-4 w-4" />
          Zone not in curated rule set
        </div>
        <p className="mt-1 text-xs text-amber-700">
          This zone is not yet supported. Standards shown may be incomplete.
          Review manually with LADBS.
        </p>
      </div>
    );
  }

  return null;
}

function SummarySection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element {
  const { assessment } = detail;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-2 flex items-center justify-between">
        <SectionHeader
          icon={<FileText className="h-4 w-4" />}
          title="Summary"
        />
        <span className="text-xs text-gray-400">
          {assessment.llm_available ? "AI-generated" : "Automated"}
        </span>
      </div>
      <p className="text-sm leading-relaxed text-gray-700">
        {assessment.summary}
      </p>
    </div>
  );
}

function ParcelFactsSection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element {
  const { parcel } = detail;
  return (
    <div className="space-y-1">
      <SectionHeader icon={<MapPin className="h-4 w-4" />} title="Parcel" />
      <KeyValue label="Address" value={parcel.address} />
      <KeyValue label="APN" value={parcel.apn ?? parcel.ain} />
      <KeyValue
        label="Lot size"
        value={
          parcel.lot_sqft ? `${parcel.lot_sqft.toLocaleString()} sqft` : null
        }
      />
      <KeyValue label="Year built" value={parcel.year_built} />
      <KeyValue label="Use" value={parcel.use_description} />
      <KeyValue label="Bedrooms" value={parcel.bedrooms} />
      <KeyValue
        label="Main sqft"
        value={parcel.sqft_main ? parcel.sqft_main.toLocaleString() : null}
      />
    </div>
  );
}

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
  ].filter(Boolean);

  return (
    <div className="space-y-1">
      <SectionHeader
        icon={<Building2 className="h-4 w-4" />}
        title="Zoning & Standards"
      />
      <KeyValue label="Zone" value={zoning.zone_string} />
      <KeyValue label="Zone class" value={zoning.zone_class} />
      <KeyValue label="Height district" value={zoning.height_district} />
      {flags.length > 0 && <KeyValue label="Flags" value={flags.join(", ")} />}
      {zoning.suffixes.length > 0 && (
        <KeyValue label="Suffixes" value={zoning.suffixes.join(", ")} />
      )}
      <div className="my-1 border-t border-gray-100" />
      <KeyValue
        label="Max height"
        value={
          standards.height_ft != null ? `${standards.height_ft} ft` : "No limit"
        }
      />
      <KeyValue
        label="Max stories"
        value={
          standards.stories != null ? String(standards.stories) : "No limit"
        }
      />
      <KeyValue
        label={standards.far_type ?? "FAR"}
        value={standards.far_or_rfa}
      />
      <KeyValue label="Front setback" value={standards.front_setback_ft} />
      <KeyValue label="Side setback" value={standards.side_setback_ft} />
      <KeyValue label="Rear setback" value={standards.rear_setback_ft} />
      <KeyValue label="Density" value={standards.density_description} />
      {standards.allowed_uses.length > 0 && (
        <div className="text-sm">
          <span className="text-gray-500">Allowed uses</span>
          <div className="mt-0.5 flex flex-wrap gap-1">
            {standards.allowed_uses.map((use) => (
              <span
                key={use}
                className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-700"
              >
                {use}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function OverlaysSection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element | null {
  const { overlays } = detail;
  const hasOverlays =
    overlays.specific_plan ??
    overlays.hpoz ??
    overlays.community_plan ??
    overlays.general_plan_lu;
  if (!hasOverlays) return null;

  return (
    <div className="space-y-1">
      <SectionHeader icon={<Shield className="h-4 w-4" />} title="Overlays" />
      {overlays.specific_plan && (
        <div className="rounded border border-orange-200 bg-orange-50 p-2 text-sm">
          <div className="font-medium text-orange-800">
            Specific Plan: {overlays.specific_plan.name}
          </div>
          {overlays.specific_plan.url &&
            isSafeUrl(overlays.specific_plan.url) && (
              <a
                href={overlays.specific_plan.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-0.5 inline-flex items-center gap-1 text-xs text-orange-600 hover:underline"
              >
                View document <ExternalLink className="h-3 w-3" />
              </a>
            )}
          <p className="mt-0.5 text-xs text-orange-700">
            Additional restrictions may apply. Review the specific plan
            document.
          </p>
        </div>
      )}
      {overlays.hpoz && (
        <div className="rounded border border-purple-200 bg-purple-50 p-2 text-sm">
          <div className="font-medium text-purple-800">
            HPOZ: {overlays.hpoz.name}
          </div>
          {overlays.hpoz.url && isSafeUrl(overlays.hpoz.url) && (
            <a
              href={overlays.hpoz.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-0.5 inline-flex items-center gap-1 text-xs text-purple-600 hover:underline"
            >
              View document <ExternalLink className="h-3 w-3" />
            </a>
          )}
          <p className="mt-0.5 text-xs text-purple-700">
            Historic preservation requirements apply. Consult HPOZ board before
            modifications.
          </p>
        </div>
      )}
      <KeyValue label="Community plan" value={overlays.community_plan} />
      <KeyValue label="General plan LU" value={overlays.general_plan_lu} />
    </div>
  );
}

function AduSection({ detail }: { detail: ParcelDetail }): React.JSX.Element {
  const { adu } = detail;
  return (
    <div className="space-y-1">
      <SectionHeader icon={<Home className="h-4 w-4" />} title="ADU" />
      <KeyValue label="Allowed" value={adu.allowed ? "Yes" : "No"} />
      {adu.allowed && (
        <>
          <KeyValue label="Max sqft" value={adu.max_sqft.toLocaleString()} />
          <KeyValue label="Setbacks" value={`${adu.setbacks_ft} ft`} />
        </>
      )}
      <p className="text-xs text-gray-500">{adu.notes}</p>
    </div>
  );
}

function ConfidenceSection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element {
  const { confidence } = detail;
  return (
    <div className="space-y-1">
      <SectionHeader icon={<Scale className="h-4 w-4" />} title="Confidence" />
      <div className="flex items-center gap-2">
        <ConfidenceBadge level={confidence.level} />
      </div>
      {confidence.reasons.length > 0 && (
        <ul className="mt-1 space-y-0.5 text-xs text-gray-600">
          {confidence.reasons.map((reason, i) => (
            <li key={i} className="flex items-start gap-1">
              <span className="mt-0.5 text-gray-400">-</span>
              {reason}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function CitationsSection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element | null {
  const { assessment } = detail;
  if (assessment.citations.length === 0) return null;

  return (
    <div className="space-y-1">
      <SectionHeader
        icon={<FileText className="h-4 w-4" />}
        title="Citations"
      />
      <ul className="space-y-0.5 text-xs">
        {assessment.citations.map((citation, i) => (
          <li key={i}>
            {citation.startsWith("http") ? (
              <a
                href={citation}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-blue-600 hover:underline"
              >
                {citation.length > 60
                  ? citation.slice(0, 57) + "..."
                  : citation}
                <ExternalLink className="h-3 w-3" />
              </a>
            ) : (
              <span className="text-gray-700">{citation}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function CaveatsSection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element | null {
  const { assessment } = detail;
  if (assessment.caveats.length === 0) return null;

  return (
    <div className="rounded border border-gray-200 bg-gray-50 p-3">
      <div className="flex items-center gap-1.5 text-xs font-medium text-gray-500">
        <Info className="h-3.5 w-3.5" />
        Disclaimers
      </div>
      <ul className="mt-1 space-y-1 text-xs text-gray-600">
        {assessment.caveats.map((caveat, i) => (
          <li key={i}>{caveat}</li>
        ))}
      </ul>
    </div>
  );
}

function MetadataSection({
  detail,
}: {
  detail: ParcelDetail;
}): React.JSX.Element | null {
  const { metadata } = detail;
  if (!metadata.data_as_of && metadata.source_urls.length === 0) return null;

  return (
    <div className="text-xs text-gray-400">
      {metadata.data_as_of && (
        <div>
          Data as of{" "}
          {new Date(metadata.data_as_of).toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </div>
      )}
      {metadata.source_urls.filter(isSafeUrl).map((url, i) => (
        <a
          key={i}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-0.5 text-gray-400 hover:text-gray-600"
        >
          Source <ExternalLink className="h-3 w-3" />
        </a>
      ))}
    </div>
  );
}

export function AssessmentPanel({
  detail,
}: AssessmentPanelProps): React.JSX.Element {
  return (
    <div className="space-y-4">
      <ScopeWarning detail={detail} />
      <SummarySection detail={detail} />
      <ParcelFactsSection detail={detail} />
      <ZoningSection detail={detail} />
      <OverlaysSection detail={detail} />
      <AduSection detail={detail} />
      <ConfidenceSection detail={detail} />
      <CitationsSection detail={detail} />
      <CaveatsSection detail={detail} />
      <MetadataSection detail={detail} />
    </div>
  );
}
