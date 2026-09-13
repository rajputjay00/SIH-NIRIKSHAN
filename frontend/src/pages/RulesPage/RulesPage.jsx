import React, { useState, useEffect } from 'react';
import { Search, Filter, RotateCw } from 'lucide-react';
import { useT } from '../../i18n/useT';
import plannedRules from '../../data/planned_rules.json';
import styles from './RulesPage.module.css';

export function RulesPage() {
  const { lang, setLang } = useT();
  const [allRules, setAllRules] = useState([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [flippedCards, setFlippedCards] = useState({});

  useEffect(() => {
    const fetchActiveRules = async () => {
      let activeList = [];
      try {
        const res = await fetch('/api/rules');
        if (res.ok) {
          const data = await res.json();
          const rulesObj = data.rules || data;
          activeList = Object.entries(rulesObj).map(([id, r]) => ({
            id,
            rule_ref: r.rule_ref || id,
            title_en: r.title_en || r.description || id,
            title_hi: r.title_hi || r.title_en || id,
            severity: r.severity || 'high',
            status: 'active',
            category: r.category || 'labelling',
            requirement: r.requirement || r.title_en || 'Mandatory legal metrology declaration check.',
            check_method: r.check_method || 'Deterministic OCR line & bbox verification',
            fix_hint: r.fix_hint || 'Ensure declaration is clearly printed on Principal Display Panel.',
            source: r.source || 'LMPC Rules 2011',
          }));
        }
      } catch (err) {
        // quiet
      }

      // Merge active + planned rules
      const merged = [...activeList, ...plannedRules];
      setAllRules(merged);
    };

    fetchActiveRules();
  }, []);

  const toggleFlip = (id) => {
    setFlippedCards((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredRules = allRules.filter((r) => {
    const matchesSearch =
      r.id.toLowerCase().includes(search.toLowerCase()) ||
      r.rule_ref.toLowerCase().includes(search.toLowerCase()) ||
      (r.title_en && r.title_en.toLowerCase().includes(search.toLowerCase())) ||
      (r.title_hi && r.title_hi.toLowerCase().includes(search.toLowerCase()));

    const matchesStatus = statusFilter === 'all' || r.status === statusFilter;
    const matchesSeverity = severityFilter === 'all' || r.severity === severityFilter;

    return matchesSearch && matchesStatus && matchesSeverity;
  });

  return (
    <div className={styles.rulesContainer}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Rules-as-Code Explorer</h1>
          <p className={styles.subtitle}>
            Legal Metrology (Packaged Commodities) Rules 2011 — Full Catalogue ({allRules.length} Rules)
          </p>
        </div>

        <button
          className={styles.selectInput}
          onClick={() => setLang(lang === 'en' ? 'hi' : 'en')}
        >
          🌐 Language: {lang === 'en' ? 'English' : 'हिन्दी'}
        </button>
      </div>

      {/* Filter Bar */}
      <div className={styles.filterBar}>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search rule ID, reference, or title..."
          className={styles.searchInput}
        />

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className={styles.selectInput}
        >
          <option value="all">All Statuses</option>
          <option value="active">Active Engine Rules</option>
          <option value="planned">Planned M3 Rules</option>
        </select>

        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className={styles.selectInput}
        >
          <option value="all">All Severities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Cards Grid */}
      <div className={styles.cardsGrid}>
        {filteredRules.map((rule) => {
          const isFlipped = Boolean(flippedCards[rule.id]);
          const title = lang === 'hi' && rule.title_hi ? rule.title_hi : rule.title_en;

          return (
            <div
              key={rule.id}
              className={`${styles.flipCard} ${isFlipped ? styles.flipped : ''}`}
              onClick={() => toggleFlip(rule.id)}
            >
              <div className={styles.flipCardInner}>
                {/* Front Side */}
                <div className={styles.cardFront}>
                  <div>
                    <div className={styles.ruleHeader}>
                      <span className={styles.ruleRef}>{rule.rule_ref}</span>
                      <span
                        className={`${styles.statusChip} ${
                          rule.status === 'active' ? styles.statusActive : styles.statusPlanned
                        }`}
                      >
                        {rule.status}
                      </span>
                    </div>

                    <div className={styles.ruleTitle}>{title}</div>
                  </div>

                  <div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--grey-500)', marginBottom: '8px' }}>
                      Severity: <strong style={{ textTransform: 'capitalize' }}>{rule.severity}</strong>
                    </div>
                    <div className={styles.flipHint}>Click to flip detail ↻</div>
                  </div>
                </div>

                {/* Back Side */}
                <div className={styles.cardBack}>
                  <div className={styles.detailSection}>
                    <div>
                      <span className={styles.detailLabel}>Requirement: </span>
                      {rule.requirement}
                    </div>
                    <div>
                      <span className={styles.detailLabel}>Nirikshan Check: </span>
                      {rule.check_method}
                    </div>
                    <div>
                      <span className={styles.detailLabel}>Fix Hint: </span>
                      {rule.fix_hint}
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--grey-500)' }}>
                    <span>Source: {rule.source}</span>
                    <span>Click to flip back ↺</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
