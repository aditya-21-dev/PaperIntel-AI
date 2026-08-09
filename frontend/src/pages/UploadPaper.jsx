import { useRef, useState } from 'react'
import Icon from '../components/Icon'
import { processPaper } from '../services/api'

const MAX_FILE_SIZE = 20 * 1024 * 1024
const PDF_MIME_TYPES = ['application/pdf', 'application/x-pdf']

const statusContent = {
  idle: { label: 'Ready for a PDF', style: 'bg-slate-100 text-slate-600', icon: 'document' },
  selected: { label: 'PDF selected', style: 'bg-indigo-100 text-indigo-800', icon: 'document' },
  uploading: { label: 'Uploading file', style: 'bg-amber-100 text-amber-800', icon: 'upload' },
  processing: { label: 'Extracting document', style: 'bg-violet-100 text-violet-800', icon: 'clock' },
  completed: { label: 'Extraction complete', style: 'bg-emerald-100 text-emerald-800', icon: 'circleCheck' },
  error: { label: 'Processing needs attention', style: 'bg-rose-100 text-rose-800', icon: 'warning' },
}

function formatFileSize(size) {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function Value({ children, empty = 'Not detected' }) {
  return children ? <>{children}</> : <span className="text-slate-400">{empty}</span>
}

function ResultSection({ title, children, className = '' }) {
  return (
    <section className={`surface-card p-5 sm:p-6 ${className}`}>
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      <div className="mt-5">{children}</div>
    </section>
  )
}

function AnalysisResults({ data }) {
  const { document, metadata, sections, references, figures, tables, statistics, warnings } = data
  const summaryStats = [
    ['Pages', document.page_count],
    ['Words', statistics.word_count.toLocaleString()],
    ['Sections', statistics.section_count],
    ['References', statistics.reference_count],
  ]

  return (
    <div className="mt-10 space-y-6" aria-live="polite">
      <div>
        <p className="eyebrow">Document extraction</p>
        <h2 className="section-title mt-2 text-2xl sm:text-3xl">Paper information</h2>
        <p className="mt-2 text-slate-600">The following data was extracted from the uploaded PDF. It has not been evaluated or scored.</p>
      </div>

      {warnings?.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" role="status">
          <p className="flex items-center gap-2 font-semibold"><Icon name="warning" className="h-5 w-5" /> Extraction warning</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {summaryStats.map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ResultSection title="Document information">
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between gap-5"><dt className="text-slate-500">Filename</dt><dd className="max-w-[65%] truncate text-right font-medium text-slate-800" title={document.filename}>{document.filename}</dd></div>
            <div className="flex justify-between gap-5"><dt className="text-slate-500">File size</dt><dd className="font-medium text-slate-800">{formatFileSize(document.file_size)}</dd></div>
            <div className="flex justify-between gap-5"><dt className="text-slate-500">Page count</dt><dd className="font-medium text-slate-800">{document.page_count}</dd></div>
            <div className="flex justify-between gap-5"><dt className="text-slate-500">Characters</dt><dd className="font-medium text-slate-800">{statistics.character_count.toLocaleString()}</dd></div>
          </dl>
        </ResultSection>

        <ResultSection title="Extraction statistics">
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between gap-5"><dt className="text-slate-500">Figures</dt><dd className="font-medium text-slate-800">{statistics.figure_count}</dd></div>
            <div className="flex justify-between gap-5"><dt className="text-slate-500">Tables</dt><dd className="font-medium text-slate-800">{statistics.table_count}</dd></div>
            <div className="flex justify-between gap-5"><dt className="text-slate-500">Empty pages</dt><dd className="font-medium text-slate-800"><Value empty="None">{statistics.empty_pages.length ? statistics.empty_pages.join(', ') : null}</Value></dd></div>
            <div className="flex justify-between gap-5"><dt className="text-slate-500">Low-text pages</dt><dd className="font-medium text-slate-800"><Value empty="None">{statistics.low_text_pages.length ? statistics.low_text_pages.join(', ') : null}</Value></dd></div>
          </dl>
        </ResultSection>
      </div>

      <ResultSection title="Metadata">
        <dl className="grid gap-5 text-sm">
          <div><dt className="font-medium text-slate-500">Title <span className="font-normal">({metadata.title_confidence} confidence)</span></dt><dd className="mt-1 text-base font-semibold text-slate-900"><Value>{metadata.title}</Value></dd></div>
          <div><dt className="font-medium text-slate-500">Authors <span className="font-normal">({metadata.authors_confidence} confidence)</span></dt><dd className="mt-1 text-slate-800"><Value>{metadata.authors.join(', ')}</Value></dd></div>
          <div><dt className="font-medium text-slate-500">Abstract <span className="font-normal">({metadata.abstract_word_count} words)</span></dt><dd className="mt-1 max-w-4xl leading-7 text-slate-700"><Value>{metadata.abstract}</Value></dd></div>
          <div><dt className="font-medium text-slate-500">Keywords</dt><dd className="mt-2 flex flex-wrap gap-2"><Value>{metadata.keywords.map((keyword) => <span key={keyword} className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-800">{keyword}</span>)}</Value></dd></div>
        </dl>
      </ResultSection>

      <ResultSection title="Detected sections">
        {sections.length ? (
          <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
            {sections.map((section) => (
              <details key={`${section.number || 'unnumbered'}-${section.title}`} className="group p-4">
                <summary className="cursor-pointer list-none pr-6 font-medium text-slate-900 marker:hidden"><span className="mr-2 text-slate-500">{section.number || '—'}</span>{section.title}<span className="ml-2 text-xs font-normal text-slate-500">pages {section.page_start}–{section.page_end}</span></summary>
                <p className="mt-3 whitespace-pre-wrap leading-7 text-slate-600"><Value empty="No body text was extracted for this section.">{section.text}</Value></p>
              </details>
            ))}
          </div>
        ) : <p className="text-sm text-slate-500">No major sections were confidently detected.</p>}
      </ResultSection>

      <div className="grid gap-6 xl:grid-cols-3">
        <ResultSection title={`References (${references.length})`}>
          {references.length ? <ol className="space-y-3 text-sm leading-6 text-slate-700">{references.map((reference) => <li key={reference.number}><span className="mr-2 font-semibold text-slate-900">[{reference.number}]</span>{reference.text}</li>)}</ol> : <p className="text-sm text-slate-500">No individual references were detected.</p>}
        </ResultSection>
        <ResultSection title={`Figures (${figures.length})`}>
          {figures.length ? <ul className="space-y-3 text-sm text-slate-700">{figures.map((figure, index) => <li key={`${figure.number}-${figure.page}-${index}`}><p className="font-medium text-slate-900">Figure {figure.number ?? 'unlabelled'} <span className="font-normal text-slate-500">· page {figure.page}</span></p><p className="mt-1"><Value>{figure.caption}</Value></p></li>)}</ul> : <p className="text-sm text-slate-500">No figure captions were detected.</p>}
        </ResultSection>
        <ResultSection title={`Tables (${tables.length})`}>
          {tables.length ? <ul className="space-y-3 text-sm text-slate-700">{tables.map((table, index) => <li key={`${table.number}-${table.page}-${index}`}><p className="font-medium text-slate-900">Table {table.number ?? 'unlabelled'} <span className="font-normal text-slate-500">· page {table.page}</span></p><p className="mt-1"><Value empty={table.detected_from === 'native_table' ? 'Native table structure detected; no caption found.' : 'No caption extracted.'}>{table.caption}</Value></p></li>)}</ul> : <p className="text-sm text-slate-500">No table captions or native tables were detected.</p>}
        </ResultSection>
      </div>
    </div>
  )
}

export default function UploadPaper() {
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState('idle')
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const inputRef = useRef(null)
  const isBusy = status === 'uploading' || status === 'processing'

  const resetFile = () => {
    setFile(null)
    setStatus('idle')
    setProgress(0)
    setError('')
    setResult(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const selectFile = (selectedFile) => {
    setError('')
    setResult(null)
    setProgress(0)
    if (!selectedFile) return
    if (!selectedFile.name?.toLowerCase().endsWith('.pdf')) {
      setFile(null)
      setStatus('error')
      setError('Only files with a .pdf extension can be processed.')
      return
    }
    if (!PDF_MIME_TYPES.includes(selectedFile.type)) {
      setFile(null)
      setStatus('error')
      setError('This file does not have a valid PDF MIME type. Please choose a PDF document.')
      return
    }
    if (selectedFile.size > MAX_FILE_SIZE) {
      setFile(null)
      setStatus('error')
      setError('The PDF is larger than the 20 MB limit.')
      return
    }
    setFile(selectedFile)
    setStatus('selected')
  }

  const handleProcess = async () => {
    if (!file || isBusy) return
    setError('')
    setResult(null)
    setProgress(0)
    setStatus('uploading')
    try {
      const data = await processPaper(file, (event) => {
        if (!event.total) return
        const nextProgress = Math.min(100, Math.round((event.loaded * 100) / event.total))
        setProgress(nextProgress)
        if (nextProgress === 100) setStatus('processing')
      })
      setProgress(100)
      setStatus('completed')
      setResult(data)
    } catch (requestError) {
      const message = requestError.response?.data?.detail || requestError.message || 'The paper could not be processed. Please try another PDF.'
      setStatus('error')
      setError(message)
    }
  }

  const currentStatus = statusContent[status]

  return (
    <div className="page-container py-12 sm:py-16">
      <div className="max-w-3xl">
        <p className="eyebrow">Module 2 · PDF processing</p>
        <h1 className="section-title mt-3">Extract your paper’s structure</h1>
        <p className="mt-4 leading-7 text-slate-600">Upload a research-paper PDF to extract its text, metadata, sections, references, figures, and tables. The document is processed temporarily and is not stored.</p>
      </div>

      <section className="surface-card mt-10 p-5 sm:p-7">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div><h2 className="text-lg font-semibold text-slate-900">Research paper PDF</h2><p className="mt-1 text-sm text-slate-500">PDF MIME type and .pdf extension required · maximum 20 MB</p></div>
          <span className={`inline-flex w-fit items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold ${currentStatus.style}`}><Icon name={currentStatus.icon} className="h-4 w-4" />{currentStatus.label}</span>
        </div>
        <input ref={inputRef} className="sr-only" type="file" accept="application/pdf,.pdf" onChange={(event) => selectFile(event.target.files?.[0])} />

        {!file ? (
          <div role="button" tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click() }} onClick={() => inputRef.current?.click()} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); selectFile(event.dataTransfer.files?.[0]) }} className={`mt-6 flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 text-center transition-colors ${dragging ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 bg-slate-50 hover:border-indigo-400 hover:bg-indigo-50/40'}`}>
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100 text-indigo-700"><Icon name="upload" className="h-6 w-6" /></span>
            <p className="mt-4 font-semibold text-slate-800">Drag and drop your PDF here</p><p className="mt-1 text-sm text-slate-500">or choose a file from your computer</p>
            <button type="button" onClick={(event) => { event.stopPropagation(); inputRef.current?.click() }} className="secondary-button mt-5">Browse files</button>
          </div>
        ) : (
          <div className="mt-6 rounded-xl border border-indigo-200 bg-indigo-50/50 p-4">
            <div className="flex items-center gap-4"><span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-white text-indigo-700 shadow-sm"><Icon name="document" className="h-5 w-5" /></span><div className="min-w-0 flex-1"><p className="truncate font-medium text-slate-900">{file.name}</p><p className="mt-1 text-sm text-slate-500">{formatFileSize(file.size)} <span aria-hidden="true">·</span> <span className="rounded bg-indigo-100 px-1.5 py-0.5 text-xs font-medium text-indigo-800">PDF · {file.type}</span></p></div><button type="button" disabled={isBusy} onClick={resetFile} className="rounded-md p-2 text-slate-500 hover:bg-white hover:text-rose-700 disabled:cursor-not-allowed disabled:opacity-50" aria-label="Remove selected file"><Icon name="close" className="h-5 w-5" /></button></div>
            {isBusy && <div className="mt-4"><div className="flex justify-between text-xs font-medium text-slate-600"><span>{status === 'processing' ? 'Processing document structure…' : 'Uploading PDF…'}</span><span>{progress}%</span></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-indigo-100"><div className="h-full rounded-full bg-indigo-700 transition-all duration-300" style={{ width: `${progress}%` }} /></div></div>}
          </div>
        )}

        {error && <div className="mt-5 flex gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert"><Icon name="warning" className="mt-0.5 h-5 w-5 shrink-0" /><p>{error}</p></div>}

        <div className="mt-6 flex flex-col gap-3 border-t border-slate-100 pt-6 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-slate-500">Only extraction is performed—no quality or compliance scores are generated.</p><button type="button" disabled={!file || isBusy} onClick={handleProcess} className="primary-button disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600 disabled:hover:bg-slate-300"><Icon name={isBusy ? 'clock' : 'fileSearch'} className="h-4 w-4" />{isBusy ? 'Processing…' : status === 'error' ? 'Retry processing' : result ? 'Process again' : 'Process paper'}</button></div>
      </section>

      {result && <AnalysisResults data={result} />}
    </div>
  )
}
