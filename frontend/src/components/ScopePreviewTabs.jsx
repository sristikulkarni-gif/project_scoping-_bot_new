import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import projectApi from '../api/projectApi';
import GanttChart from './GanttChart';

import ReactFlowDiagram from './ReactFlowDiagram';


/**
 * Component to render scope section previews
 */
const ScopePreviewTabs = ({ activeTab, parsedDraft }) => {
  const { id: projectId } = useParams();
  const [caseStudy, setCaseStudy] = useState(null);
  const [caseStudyLoading, setCaseStudyLoading] = useState(false);
  const [caseStudyError, setCaseStudyError] = useState(null);

  // Extract inferred fields list from scope JSON (set by backend during generation)
  const inferredFields = Array.isArray(parsedDraft?.inferred_fields)
    ? parsedDraft.inferred_fields
    : [];

  // Fetch related case study when tab is active
  useEffect(() => {
    if (activeTab === 'related_case_study' && projectId) {
      const fetchCaseStudy = async () => {
        try {
          setCaseStudyLoading(true);
          setCaseStudyError(null);
          const response = await projectApi.getRelatedCaseStudy(projectId);
          setCaseStudy(response.data);
        } catch (error) {
          console.error('Failed to fetch related case study:', error);
          setCaseStudyError(error.response?.data?.detail || 'Failed to load related case study');
        } finally {
          setCaseStudyLoading(false);
        }
      };
      fetchCaseStudy();
    }
  }, [activeTab, projectId]);

  if (!parsedDraft) {
    return (
      <div className="text-center text-gray-500 dark:text-gray-400 py-12">
        <p>No scope data available. Please finalize the scope first.</p>
      </div>
    );
  }

  // Debug: Log the structure
  console.log('ScopePreviewTabs - activeTab:', activeTab);
  console.log('ScopePreviewTabs - parsedDraft keys:', Object.keys(parsedDraft));
  console.log('ScopePreviewTabs - parsedDraft:', parsedDraft);

  // Helper to render table from array of objects or array of arrays
  const renderTable = (data, title = '') => {
    if (!Array.isArray(data) || data.length === 0) {
      return <div className="text-gray-500 italic">No data available</div>;
    }

    // Check if data is array of objects
    if (typeof data[0] === 'object' && !Array.isArray(data[0])) {
      const allHeaders = Object.keys(data[0]);

      // Filter out columns that are completely empty across all rows
      const headers = allHeaders.filter(header => {
        return data.some(row => {
          const val = row[header];
          return val !== null && val !== undefined && val !== '' && val !== 'null';
        });
      });

      // Check if this is a resourcing plan (has "Cost" column)
      const isResourcingPlan = headers.includes('Cost') || headers.includes('cost');
      let totalCost = 0;

      if (isResourcingPlan) {
        // Calculate total cost
        data.forEach(row => {
          const cost = parseFloat(row.Cost || row.cost || 0);
          if (!isNaN(cost)) {
            totalCost += cost;
          }
        });
      }

      return (
        <div className="overflow-x-auto">
          {title && <h4 className="font-semibold text-gray-800 dark:text-gray-200 mb-2">{title}</h4>}
          <table className="min-w-full border border-gray-300 dark:border-gray-600">
            <thead className="bg-gray-100 dark:bg-gray-700">
              <tr>
                {headers.map((header, idx) => (
                  <th key={idx} className="px-4 py-2 text-left text-sm font-semibold text-gray-700 dark:text-gray-200 border-b border-gray-300 dark:border-gray-600">
                    {header.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, rowIdx) => (
                <tr key={rowIdx} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                  {headers.map((header, colIdx) => (
                    <td key={colIdx} className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                      {typeof row[header] === 'object' ? JSON.stringify(row[header]) : (row[header] !== null && row[header] !== undefined && row[header] !== '') ? String(row[header]) : '-'}
                    </td>
                  ))}
                </tr>
              ))}
              {/* Add Total Cost Row for Resourcing Plan */}
              {isResourcingPlan && (
                <tr className="bg-blue-50 dark:bg-blue-900/20 font-bold">
                  {headers.map((header, colIdx) => (
                    <td key={colIdx} className="px-4 py-3 text-sm border-t-2 border-blue-500 dark:border-blue-400">
                      {header === 'Resources' || header === 'resources' ? (
                        <span className="text-blue-900 dark:text-blue-100">Total Project Cost</span>
                      ) : header === 'Cost' || header === 'cost' ? (
                        <span className="text-blue-900 dark:text-blue-100">${totalCost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                  ))}
                </tr>
              )}
            </tbody>
          </table>
        </div>
      );
    }

    // If array of arrays, render as simple table
    if (Array.isArray(data[0])) {
      return (
        <div className="overflow-x-auto">
          {title && <h4 className="font-semibold text-gray-800 dark:text-gray-200 mb-2">{title}</h4>}
          <table className="min-w-full border border-gray-300 dark:border-gray-600">
            <tbody>
              {data.map((row, rowIdx) => (
                <tr key={rowIdx} className={rowIdx === 0 ? "bg-gray-100 dark:bg-gray-700" : "hover:bg-gray-50 dark:hover:bg-gray-800"}>
                  {row.map((cell, cellIdx) => (
                    <td key={cellIdx} className={`px-4 py-2 text-sm ${rowIdx === 0 ? 'font-semibold text-gray-700 dark:text-gray-200' : 'text-gray-600 dark:text-gray-400'} border-b border-gray-200 dark:border-gray-700`}>
                      {String(cell || '-')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    // Fallback: render as list
    return (
      <ul className="list-disc list-inside space-y-1 ml-4">
        {data.map((item, idx) => (
          <li key={idx} className="text-gray-600 dark:text-gray-400">
            {String(item)}
          </li>
        ))}
      </ul>
    );
  };

  const renderValue = (value, depth = 0) => {
    if (value === null || value === undefined || value === '') return null;

    // Prevent infinite recursion
    if (depth > 5) {
      return <span className="text-gray-500 italic">...</span>;
    }

    if (Array.isArray(value)) {
      if (value.length === 0) return <span className="text-gray-500 italic">None</span>;

      // Check if this looks like tabular data
      if (value.length > 0 && typeof value[0] === 'object') {
        return renderTable(value);
      }

      return (
        <ul className="list-disc list-inside space-y-1 ml-4">
          {value.map((item, idx) => (
            <li key={idx} className="text-gray-600 dark:text-gray-400">
              {typeof item === 'object' ? renderValue(item, depth + 1) : String(item)}
            </li>
          ))}
        </ul>
      );
    } else if (typeof value === 'object') {
      return (
        <div className="ml-4 mt-2 space-y-2">
          {Object.entries(value).map(([k, v]) => {
            if (v === null || v === undefined || v === '') return null;
            return (
              <div key={k} className="flex gap-2">
                <span className="font-medium text-gray-700 dark:text-gray-300 min-w-[150px]">
                  {k.replace(/_/g, ' ')}:
                </span>
                <div className="flex-1">{renderValue(v, depth + 1)}</div>
              </div>
            );
          })}
        </div>
      );
    } else {
      return <span className="text-gray-600 dark:text-gray-400">{String(value)}</span>;
    }
  };

  const renderSection = (data, isTableSection = false, isImageSection = false) => {
    if (!data) {
      return <div className="text-gray-500 italic">No data available</div>;
    }

    // Special rendering for overview tab - show as modern card grid
    if (activeTab === 'overview' && typeof data === 'object' && !Array.isArray(data)) {
      return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-auto">
          {Object.entries(data).map(([key, value], idx) => {
            const isInferred = inferredFields.includes(key);
            return (
              <div
                key={idx}
                className={`rounded-lg p-4 hover:shadow-md transition-shadow duration-200 flex flex-col border ${isInferred
                  ? 'border-yellow-400 bg-yellow-50 dark:bg-yellow-900/20'
                  : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'
                  }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="text-sm font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                    {key.replace(/_/g, ' ')}
                  </div>
                  {isInferred && (
                    <span
                      title="AI Inferred — Please Verify"
                      className="cursor-help text-xs font-semibold text-yellow-700 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/40 border border-yellow-300 dark:border-yellow-600 rounded-full px-2 py-0.5 flex items-center gap-1 ml-2 shrink-0"
                    >
                      ⚠️ AI Inferred
                    </span>
                  )}
                </div>
                <div className="text-base text-gray-900 dark:text-gray-100 break-words flex-grow">
                  {typeof value === 'object' ? JSON.stringify(value) : String(value || '-')}
                </div>
              </div>
            );
          })}
        </div>
      );
    }

    // Special rendering for cost projection - show total_cost prominently at the top
    if (activeTab === 'costing' && typeof data === 'object' && !Array.isArray(data)) {
      const formatCurrency = (amount) => {
        if (typeof amount === 'number') {
          return `$${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }
        return amount;
      };

      return (
        <div className="space-y-6">
          {/* Total Cost - Prominently displayed at top */}
          {data.total_cost !== undefined && (
            <div className="bg-emerald-50 dark:bg-emerald-900/20 border-2 border-emerald-500 rounded-lg p-6 mb-6">
              <h3 className="text-2xl font-bold text-emerald-700 dark:text-emerald-400 mb-2">
                Total Project Cost
              </h3>
              <p className="text-4xl font-bold text-emerald-900 dark:text-emerald-300">
                {formatCurrency(data.total_cost)}
              </p>
              {data.currency && (
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Currency: {data.currency}
                </p>
              )}
              {data.discount_percentage > 0 && (
                <p className="text-sm text-emerald-700 dark:text-emerald-400 mt-2">
                  ✓ Includes {data.discount_percentage}% discount ({formatCurrency(data.discount_amount)} off)
                </p>
              )}
            </div>
          )}

          {/* Render rest of cost breakdown */}
          {Object.entries(data).map(([key, value]) => {
            if (value === null || value === undefined || value === '') return null;
            // Skip total_cost, currency, discount fields as they're shown above
            if (key === 'total_cost' || key === 'currency' || key === 'discount_percentage' || key === 'discount_amount') return null;

            return (
              <div key={key} className="border-b border-gray-200 dark:border-gray-700 pb-4 last:border-0">
                <h4 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
                  {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </h4>
                <div className="ml-4">
                  {renderValue(value)}
                </div>
              </div>
            );
          })}
        </div>
      );
    }

    // If this is the architecture section and data is an object (React Flow JSON)
    if (isImageSection && typeof data === 'object' && data.nodes && data.edges) {
      return <ReactFlowDiagram data={data} />;
    }

    // Fallback for legacy string paths
    if (isImageSection && typeof data === 'string') {
      if (data.match(/\.(png|jpg|jpeg|gif|svg|webp)$/i)) {
        const imageUrl = `/api/blobs/download/${data}?base=projects`;
        return (
          <div className="flex justify-center p-4">
            <img src={imageUrl} alt="Legacy Architecture Diagram" className="max-w-full rounded-lg shadow-md" />
          </div>
        );
      }
      return <div className="text-gray-600 dark:text-gray-400">{data}</div>;
    }

    if (typeof data !== 'object') {
      return <div className="text-gray-500 italic">No data available</div>;
    }

    // If this is marked as a table section and data is an array, render as table
    if (isTableSection && Array.isArray(data)) {
      return renderTable(data);
    }

    // If data is an array of objects at top level, render as table
    if (Array.isArray(data) && data.length > 0 && typeof data[0] === 'object') {
      return renderTable(data);
    }

    return (
      <div className="space-y-6">
        {Object.entries(data).map(([key, value]) => {
          if (value === null || value === undefined || value === '') return null;

          return (
            <div key={key} className="border-b border-gray-200 dark:border-gray-700 pb-4 last:border-0">
              <h4 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
                {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </h4>
              <div className="ml-4">
                {renderValue(value)}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const getSectionData = () => {
    // Try multiple field name variations (case-insensitive)
    const findField = (...names) => {
      for (const name of names) {
        // Try exact match
        if (parsedDraft[name]) {
          console.log(`✓ Found exact match for "${name}"`);
          return parsedDraft[name];
        }

        // Try case-insensitive match
        const lowerName = name.toLowerCase();
        const foundKey = Object.keys(parsedDraft).find(k => k.toLowerCase() === lowerName);
        if (foundKey && parsedDraft[foundKey]) {
          console.log(`✓ Found case-insensitive match: "${foundKey}" for search term "${name}"`);
          return parsedDraft[foundKey];
        }
      }

      // Try partial match as last resort (contains the key words)
      for (const name of names) {
        const searchTerms = name.toLowerCase().split(/[\s_-]+/);
        const foundKey = Object.keys(parsedDraft).find(k => {
          const keyLower = k.toLowerCase();
          return searchTerms.every(term => keyLower.includes(term));
        });
        if (foundKey && parsedDraft[foundKey]) {
          console.log(`✓ Found partial match: "${foundKey}" for search terms "${name}"`);
          return parsedDraft[foundKey];
        }
      }

      console.log(`✗ No match found for any of: ${names.join(', ')}`);
      return null;
    };

    let sectionData = null;

    switch (activeTab) {
      case 'overview':
        sectionData = findField('overview', 'project_overview', 'Overview', 'Project Overview', 'project overview');
        break;
      case 'activities':
      case 'gantt': // Gantt tab uses same data as activities
        sectionData = findField('activities', 'activities_breakdown', 'Activities Breakdown', 'Activities', 'activity_breakdown', 'activities breakdown');
        break;
      case 'resourcing':
        // Try resourcing_plan FIRST (most specific), then resourcing (might be empty)
        sectionData = findField('resourcing_plan', 'Resourcing Plan', 'resourcing', 'Resourcing', 'resource_plan', 'resources', 'resourcing plan');
        break;
      case 'architecture':
        sectionData = findField('architecture_diagram', 'architecture', 'Architecture', 'Architecture Diagram', 'Architecture diagram', 'arch_diagram', 'architecture diagram', 'system architecture', 'technical architecture');
        break;
      case 'costing':
        sectionData = findField('cost', 'cost_projection', 'costing', 'Cost Projection', 'cost_breakdown', 'pricing', 'Costing', 'costs', 'budget', 'cost projection', 'financial projection', 'cost estimate');
        break;
      case 'summary':
        // Try project_summary FIRST (most specific), also try risks as fallback
        sectionData = findField('project_summary', 'summary', 'risks', 'Summary', 'Summery', 'Project Summary', 'executive_summary', 'project summary');
        break;
      default:
        sectionData = null;
    }

    console.log('ScopePreviewTabs - sectionData for', activeTab, ':', sectionData);

    // If no section-specific data, check if parsedDraft itself might be the section
    if (!sectionData && activeTab === 'overview') {
      sectionData = parsedDraft;
    }

    return sectionData;
  };

  const sectionData = getSectionData();
  const isTableSection = activeTab === 'activities' || activeTab === 'resourcing';
  const isImageSection = activeTab === 'architecture';

  // Handle Tech Stack tab
  if (activeTab === 'tech_stack') {
    const techStack = parsedDraft?.recommended_tech_stack || [];
    const categoryIcons = {
      Frontend: { icon: "🖥️", color: "#7c3aed" },
      Backend: { icon: "⚙️", color: "#06b6d4" },
      Database: { icon: "🗄️", color: "#10b981" },
      Infrastructure: { icon: "☁️", color: "#f59e0b" },
      DevOps: { icon: "🚀", color: "#8b5cf6" },
      "AI/ML": { icon: "🤖", color: "#ec4899" },
      Mobile: { icon: "📱", color: "#f97316" },
    };
    return (
      <div className="p-6 space-y-4" style={{ background: "#0a0d1a" }}>
        <div className="mb-4">
          <h2 className="text-lg font-bold text-white">Recommended Tech Stack</h2>
          <p className="text-sm text-slate-500">AI-selected technologies based on the project domain and RFP requirements.</p>
        </div>
        {techStack.length === 0 ? (
          <div className="text-center py-16 text-slate-500">
            <p className="text-4xl mb-3">🛠️</p>
            <p className="font-medium">No tech stack data yet.</p>
            <p className="text-xs mt-1">Regenerate the scope to get AI-recommended technologies.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {techStack.map((cat, idx) => {
              const meta = categoryIcons[cat.category] || { icon: "🔧", color: "#64748b" };
              return (
                <div
                  key={idx}
                  className="rounded-2xl p-5"
                  style={{
                    background: "#131929",
                    border: "1px solid rgba(255,255,255,0.07)",
                    boxShadow: "0 4px 24px rgba(0,0,0,0.3)"
                  }}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xl">{meta.icon}</span>
                    <h3 className="font-bold text-sm text-white">{cat.category}</h3>
                  </div>
                  <div className="flex flex-wrap gap-2.5 mt-1">
                    {(cat.technologies || []).map((techStr, ti) => {
                      // Parse "Tech Name (Classification)" or "Tech Name - Classification"
                      let name = techStr;
                      let classification = null;

                      const parensMatch = techStr.match(/^(.*?)\s*\((.*?)\)$/);
                      if (parensMatch && (parensMatch[2].toLowerCase().includes('explicit') || parensMatch[2].toLowerCase().includes('implicit'))) {
                        name = parensMatch[1].trim();
                        classification = parensMatch[2].trim();
                      } else {
                        const dashMatch = techStr.match(/^(.*?)\s+-\s+(Explicit.*?|Implicit.*?)$/i);
                        if (dashMatch) {
                          name = dashMatch[1].trim();
                          classification = dashMatch[2].trim();
                        }
                      }

                      let classBadge = null;
                      if (classification) {
                        const isExplicit = classification.toLowerCase().includes('explicit');
                        const isImplicit = classification.toLowerCase().includes('implicit');

                        if (isExplicit) {
                          classBadge = <span className="ml-2 flex-shrink-0 text-[9px] uppercase tracking-wider font-bold bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded-sm border border-emerald-500/30 shadow-sm" title={classification}>Explicit</span>;
                        } else if (isImplicit) {
                          classBadge = <span className="ml-2 flex-shrink-0 text-[9px] uppercase tracking-wider font-bold bg-indigo-500/20 text-indigo-300 px-1.5 py-0.5 rounded-sm border border-indigo-500/30 shadow-sm" title={classification}>Implicit</span>;
                        } else {
                          classBadge = <span className="ml-2 flex-shrink-0 text-[9px] uppercase tracking-wider font-bold bg-white/10 text-white/70 px-1.5 py-0.5 rounded-sm border border-white/20 shadow-sm" title={classification}>{classification}</span>;
                        }
                      }

                      return (
                        <div
                          key={ti}
                          className="text-sm font-medium pl-3 pr-2 py-1.5 rounded-lg flex items-center shadow-lg"
                          style={{
                            background: `${meta.color}15`,
                            color: meta.color,
                            border: `1px solid ${meta.color}40`,
                            backdropFilter: 'blur(4px)'
                          }}
                          title={techStr}
                        >
                          <span className="truncate">{name}</span>
                          {classBadge}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // Handle Related Case Study tab separately
  if (activeTab === 'related_case_study') {
    return (
      <div className="p-6 bg-white dark:bg-dark-card rounded-lg border border-gray-200 dark:border-gray-700 max-h-[600px] overflow-y-auto">
        {caseStudyLoading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-primary border-t-transparent"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">Loading related case study...</p>
          </div>
        ) : caseStudyError ? (
          <div className="text-center py-12 text-red-600 dark:text-red-400">
            <p className="font-semibold mb-2">Error</p>
            <p className="text-sm">{caseStudyError}</p>
          </div>
        ) : caseStudy?.case_study ? (
          <div className="space-y-6">
            {caseStudy.matched ? (
              <div className="bg-green-50 dark:bg-green-900/20 border-2 border-green-500 rounded-lg p-4 mb-6">
                <p className="text-sm text-green-700 dark:text-green-400">
                  ✓ Found matching case study with {(caseStudy.similarity_score * 100).toFixed(1)}% similarity
                </p>
              </div>
            ) : caseStudy.pending_approval ? (
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border-2 border-yellow-500 rounded-lg p-4 mb-6">
                <p className="text-sm text-yellow-700 dark:text-yellow-400 font-semibold">
                  ⚠️ AI-Generated Case Study — Pending Admin Approval
                </p>
                <p className="text-xs text-yellow-600 dark:text-yellow-500 mt-1">
                  This case study was automatically generated by AI based on project requirements. An admin needs to review and approve it before it becomes available for matching.
                </p>
              </div>
            ) : null}

            <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
              <h4 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
                Client Name
              </h4>
              <div className="ml-4">
                <span className="text-gray-600 dark:text-gray-400">{caseStudy.case_study.client_name || '-'}</span>
              </div>
            </div>

            <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
              <h4 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
                Overview
              </h4>
              <div className="ml-4">
                <span className="text-gray-600 dark:text-gray-400">{caseStudy.case_study.overview || '-'}</span>
              </div>
            </div>

            <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
              <h4 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
                Solution
              </h4>
              <div className="ml-4">
                <span className="text-gray-600 dark:text-gray-400">{caseStudy.case_study.solution || '-'}</span>
              </div>
            </div>

            <div className="pb-4">
              <h4 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
                Impact
              </h4>
              <div className="ml-4">
                <span className="text-gray-600 dark:text-gray-400">{caseStudy.case_study.impact || '-'}</span>
              </div>
            </div>

            {caseStudy.case_study.file_name && (
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
                Source: {caseStudy.case_study.file_name}
                {caseStudy.case_study.slide_range && ` (Slides ${caseStudy.case_study.slide_range})`}
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="text-gray-500 dark:text-gray-400 mb-4">
              <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="text-lg font-medium text-gray-700 dark:text-gray-300">
              No matching case study was found in the provided PPT files.
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              Upload case studies to the Knowledge Base to enable matching.
            </p>
          </div>
        )}
      </div>
    );
  }

  if (activeTab === 'gantt') {
    return (
      <div className="p-6 bg-white dark:bg-dark-card rounded-lg border border-gray-200 dark:border-gray-700 overflow-x-auto">
        {sectionData ? (
          <GanttChart activities={sectionData} />
        ) : (
          <div className="text-center text-gray-500 italic py-8">
            <p>No activity data available for Gantt chart.</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="p-6 bg-white dark:bg-dark-card rounded-lg border border-gray-200 dark:border-gray-700 max-h-[600px] overflow-y-auto">
      {sectionData ? renderSection(sectionData, isTableSection, isImageSection) : (
        <div className="text-center text-gray-500 italic py-8">
          <p className="mb-2">This section has no data in the current scope</p>
          <p className="text-sm font-medium mb-2">Available fields in scope:</p>
          <div className="text-xs bg-gray-100 dark:bg-gray-800 p-3 rounded inline-block text-left">
            {Object.keys(parsedDraft).map((key, idx) => (
              <div key={idx}>• {key}</div>
            ))}
          </div>
          {activeTab === 'costing' && (
            <p className="mt-4 text-sm text-amber-600 dark:text-amber-400">
              💡 Tip: The AI model didn't generate a cost projection section for this scope. You may want to regenerate the scope or add costing details manually.
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default ScopePreviewTabs;