"use client";

import React, { ReactNode } from "react";
import styles from "./Card.module.css";

interface CardProps {
  title?: string;
  subtitle?: string;
  icon?: ReactNode;
  children?: ReactNode;
  className?: string;
  hoverable?: boolean;
}

export function Card({ title, subtitle, icon, children, className = "", hoverable = false }: CardProps) {
  return (
    <div className={`${styles.card} ${hoverable ? styles.hoverable : ""} ${className}`}>
      {(title || icon) && (
        <div className={styles.header}>
          {icon && <span className={styles.icon}>{icon}</span>}
          <div className={styles.headerText}>
            {title && <h3 className={styles.title}>{title}</h3>}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
        </div>
      )}
      {children && <div className={styles.body}>{children}</div>}
    </div>
  );
}
