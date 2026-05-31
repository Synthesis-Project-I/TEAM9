import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

type Recommendation = {
  ML_PREDICTED_SCORE?: number
  NAME: string
  AVERAGE_QUALITY?: number
  ON_TIME_SCORE?: number
  DAILY_CAPACITY?: number
  [key: string]: string | number | undefined
}

export default function Page() {
  const [companyName, setCompanyName] = useState("Appcelerate")
  const [languagePair, setLanguagePair] = useState("English_Spanish (LA)")
  const [taskType, setTaskType] = useState("ProofReading")
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")

  const loadRecommendations = async () => {
    setLoading(true)
    setMessage("")
    try {
      const apiBaseUrl = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8010"
      const params = new URLSearchParams({
        company_name: companyName,
        task_date: "2024-10-10",
        task_deadline: "2024-10-12",
        task_start_time: "09:00",
        task_end_time: "17:00",
        task_length_hours: "3.5",
        language_pair: languagePair,
        task_type: taskType,
        top_n: "10",
      })
      const response = await fetch(`${apiBaseUrl}/recommendations?${params}`)
      const result = await response.json()
      setRecommendations(result.data ?? [])
      setMessage(result.message ?? "")
    } catch (error) {
      console.error(error)
      setMessage("Could not load recommendations")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-4 px-4 lg:px-6">
      <div className="grid gap-3 md:grid-cols-4">
        <Input value={companyName} onChange={(event) => setCompanyName(event.target.value)} />
        <Input value={languagePair} onChange={(event) => setLanguagePair(event.target.value)} />
        <Input value={taskType} onChange={(event) => setTaskType(event.target.value)} />
        <Button onClick={loadRecommendations} disabled={loading}>
          {loading ? "Loading" : "Recommend"}
        </Button>
      </div>

      {message && <div className="text-sm text-muted-foreground">{message}</div>}

      <div className="overflow-hidden rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Score</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Quality</TableHead>
              <TableHead>On Time</TableHead>
              <TableHead>Capacity</TableHead>
              <TableHead>Rate</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {recommendations.map((row, index) => (
              <TableRow key={`${row.NAME}-${index}`}>
                <TableCell>{typeof row.ML_PREDICTED_SCORE === "number" ? row.ML_PREDICTED_SCORE.toFixed(4) : ""}</TableCell>
                <TableCell>{row.NAME}</TableCell>
                <TableCell>{row.AVERAGE_QUALITY}</TableCell>
                <TableCell>{row.ON_TIME_SCORE}</TableCell>
                <TableCell>{row.DAILY_CAPACITY}</TableCell>
                <TableCell>{row[languagePair]}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
