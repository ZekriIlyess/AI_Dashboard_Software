import ConnectionWizard from "@/components/connections/ConnectionWizard";

export default function ConnectionsPage() {
  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem', color: '#fff' }}>Database Connections</h1>
        <p style={{ color: 'var(--color-text-muted)' }}>
          Connect DataChat to your data warehouse securely. We only require read-only access.
        </p>
      </div>
      
      <ConnectionWizard />
    </div>
  );
}
