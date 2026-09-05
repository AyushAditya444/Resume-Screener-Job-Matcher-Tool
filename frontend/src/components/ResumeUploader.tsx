import { useState } from 'react';

interface Props {
  onFileSelected: (file: File) => void;
  busy: boolean;
}

export default function ResumeUploader({ onFileSelected, busy }: Props) {
  const [fileName, setFileName] = useState<string | null>(null);

  return (
    <div>
      <input
        type="file"
        accept=".pdf,.docx"
        disabled={busy}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            setFileName(file.name);
            onFileSelected(file);
          }
        }}
      />
      {fileName && <p>Selected: {fileName}</p>}
    </div>
  );
}
