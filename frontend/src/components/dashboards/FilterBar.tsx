"use client";

import React, { useState } from "react";
import { Filter, Calendar, Search } from "lucide-react";
import styles from "./FilterBar.module.css";

interface FilterBarProps {
  onSearchChange?: (val: string) => void;
  onDateChange?: (range: { start: string; end: string }) => void;
}

export function FilterBar({ onSearchChange, onDateChange }: FilterBarProps) {
  const [searchVal, setSearchVal] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchVal(e.target.value);
    if (onSearchChange) {
      onSearchChange(e.target.value);
    }
  };

  const handleDateApply = () => {
    if (onDateChange && startDate && endDate) {
      onDateChange({ start: startDate, end: endDate });
    }
  };

  return (
    <div className={styles.bar}>
      <div className={styles.searchWrapper}>
        <Search size={16} className={styles.searchIcon} />
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Filter dashboards/widgets..."
          value={searchVal}
          onChange={handleSearch}
        />
      </div>

      <div className={styles.dateWrapper}>
        <Calendar size={16} className={styles.dateIcon} />
        <input
          type="date"
          className={styles.dateInput}
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
        />
        <span className={styles.divider}>to</span>
        <input
          type="date"
          className={styles.dateInput}
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
        />
        <button
          type="button"
          className={`btn btn-secondary ${styles.applyBtn}`}
          onClick={handleDateApply}
        >
          Apply
        </button>
      </div>
    </div>
  );
}
