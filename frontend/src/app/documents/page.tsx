"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Upload,
  FileText,
  Trash2,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { api, streamUpload } from "@/lib/api";

interface Document {
  doc_id: string;
  filename: string;
  title?: string;
  author?: string;
  chunk_count: number;
  indexed_at?: string;
}

interface IngestLog {
  stage: string;
  message: string;
  status: string;
  timestamp: number;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [ingestLogs, setIngestLogs] = useState<IngestLog[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const data = await api.listDocuments();
      setDocuments(data.documents ?? []);
      setTotalChunks(data.total_chunks ?? 0);
    } catch { /* backend offline */ }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Auto-scroll logs
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [ingestLogs]);

  const handleUpload = (file: File) => {
    setIsUploading(true);
    setUploadProgress(0);
    setIngestLogs([]);

    streamUpload(
      file,
      (data) => {
        const progress = (data.progress as number) ?? 0;
        setUploadProgress(Math.round(progress * 100));

        setIngestLogs((prev) => [
          ...prev,
          {
            stage: data.stage as string,
            message: data.message as string,
            status: data.status as string,
            timestamp: Date.now(),
          },
        ]);
      },
      () => {
        setIsUploading(false);
        setUploadProgress(100);
        fetchDocuments();
        // Clear logs after 5 seconds on success to clean up UI
        setTimeout(() => setIngestLogs([]), 5000);
      },
      (err) => {
        setIsUploading(false);
        setIngestLogs((prev) => [
          ...prev,
          { stage: "error", message: err, status: "error", timestamp: Date.now() },
        ]);
      }
    );
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const handleDelete = async (docId: string) => {
    await api.deleteDocument(docId);
    fetchDocuments();
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold">
        <span className="text-primary">Document</span> Manager
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload Area */}
        <Card className="glass border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Upload Document</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
                dragOver
                  ? "border-primary bg-primary/5 scale-[1.02]"
                  : "border-border hover:border-primary/50"
              }`}
              onClick={() => {
                const input = document.createElement("input");
                input.type = "file";
                input.accept = ".pdf,.epub";
                input.onchange = (e) => {
                  const file = (e.target as HTMLInputElement).files?.[0];
                  if (file) handleUpload(file);
                };
                input.click();
              }}
            >
              <Upload className="h-8 w-8 mx-auto mb-3 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Drop PDF or ePub here, or click to browse
              </p>
            </div>

            {/* Progress */}
            {isUploading && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Ingesting...</span>
                  <span className="text-primary font-mono">{uploadProgress}%</span>
                </div>
                <Progress value={uploadProgress} className="h-2" />
              </div>
            )}

            {/* Ingest Logs */}
            {ingestLogs.length > 0 && (
              <ScrollArea className="mt-4 h-40 rounded-lg bg-background/50 p-3">
                <div className="terminal-log space-y-1">
                  {ingestLogs.map((log, i) => (
                    <div key={i} className="flex items-start gap-2">
                      {log.status === "error" ? (
                        <AlertCircle className="h-3 w-3 mt-0.5 text-destructive flex-shrink-0" />
                      ) : log.status === "done" ? (
                        <CheckCircle2 className="h-3 w-3 mt-0.5 text-neon-green flex-shrink-0" />
                      ) : i === ingestLogs.length - 1 && isUploading ? (
                        <Loader2 className="h-3 w-3 mt-0.5 text-primary animate-spin flex-shrink-0" />
                      ) : (
                        <span className="h-3 w-3 mt-0.5 flex-shrink-0 flex items-center justify-center text-primary/50 text-[10px]">▶</span>
                      )}
                      <span
                        className={
                          log.status === "error"
                            ? "text-destructive"
                            : log.status === "done"
                            ? "text-neon-green"
                            : "text-primary"
                        }
                      >
                        [{log.stage}] {log.message}
                      </span>
                    </div>
                  ))}
                  <div ref={scrollRef} />
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* Document List */}
        <Card className="glass border-border/50">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">
                Indexed Documents
              </CardTitle>
              <Badge variant="outline" className="text-xs">
                {totalChunks} chunks
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[320px]">
              {documents.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground text-sm">
                  <FileText className="h-8 w-8 mb-2 opacity-30" />
                  No documents indexed yet
                </div>
              ) : (
                <div className="space-y-2">
                  {documents.map((doc) => (
                    <div
                      key={doc.doc_id}
                      className="flex items-center gap-3 p-3 rounded-lg bg-secondary/30 border border-border/30 hover:bg-secondary/50 transition-all group"
                    >
                      <FileText className="h-5 w-5 text-primary flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {doc.filename}
                        </p>
                        <p className="text-[11px] text-muted-foreground">
                          {doc.chunk_count} chunks
                          {doc.author && ` | ${doc.author}`}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:text-destructive"
                        onClick={() => handleDelete(doc.doc_id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
