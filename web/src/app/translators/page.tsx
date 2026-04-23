import { DataTable } from "@/components/data-table"
import { type ColumnDef } from "@tanstack/react-table"
import React, { useState, useEffect } from 'react'

function DragHandle({ id }: { id: number }) {
  const { attributes, listeners } = useSortable({
    id,
  })

  return (
    <Button
      {...attributes}
      {...listeners}
      variant="ghost"
      size="icon"
      className="size-7 text-muted-foreground hover:bg-transparent"
    >
      <GripVerticalIcon className="size-3 text-muted-foreground" />
      <span className="sr-only">Drag to reorder</span>
    </Button>
  )
}

import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  MouseSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type UniqueIdentifier,
} from "@dnd-kit/core"
import { restrictToVerticalAxis } from "@dnd-kit/modifiers"
import {
  arrayMove,
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import {
  flexRender,
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type ColumnFiltersState,
  type Row,
  type SortingState,
  type VisibilityState,
} from "@tanstack/react-table"
import { Area, AreaChart, CartesianGrid, XAxis } from "recharts"
import { toast } from "sonner"
import { z } from "zod"

import { useIsMobile } from "@/hooks/use-mobile"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import { GripVerticalIcon, CircleCheckIcon, LoaderIcon, EllipsisVerticalIcon, Columns3Icon, ChevronDownIcon, PlusIcon, ChevronsLeftIcon, ChevronLeftIcon, ChevronRightIcon, ChevronsRightIcon, TrendingUpIcon } from "lucide-react"

type Translator = {
  index: number
  HOURLY_RATE: number
  SOURCE_LANG: string
  TARGET_LANG: string
  TRANSLATOR: string
}

const columns: ColumnDef<Translator>[] = [
  {
    id: "drag",
    header: () => null,
    cell: ({ row }) => <DragHandle id={row.original.index} />,
  },
  {
    id: "select",
    header: ({ table }) => (
      <div className="flex items-center justify-center">
        <Checkbox
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && "indeterminate")
          }
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      </div>
    ),
    cell: ({ row }) => (
      <div className="flex items-center justify-center">
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
        />
      </div>
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "TRANSLATOR",
    header: "Name",
    cell: ({ row }) => (
      <h1>
        {row.original.TRANSLATOR}
      </h1>
    ),
  },
  {
    accessorKey: "SOURCE_LANG",
    header: "Source Language",
    cell: ({ row }) => (
      <div className="w-32">
        <Badge variant="outline" className="px-1.5 text-muted-foreground">
          {row.original.SOURCE_LANG}
        </Badge>
      </div>
    ),
  },  
  {
    accessorKey: "TARGET_LANG",
    header: "Target Language",
    cell: ({ row }) => (
      <div className="w-32">
        <Badge variant="outline" className="px-1.5 text-muted-foreground">
          {row.original.TARGET_LANG}
        </Badge>
      </div>
    ),
  },
  {
    accessorKey: "HOURLY_RATE",
    header: "Hourly Rate",
    cell: ({ row }) => (
      <h1>
          {row.original.HOURLY_RATE}$
      </h1>
    ),
  },

  ]

export default function Page() {
  const [data, setData] = useState<Translator[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [pageSize, setPageSize] = useState(50)
  const [pageIndex, setPageIndex] = useState(1)
  const [pageCount, setPageCount] = useState(10)
  const [asc, setAsc] = useState(true)
  const [sortBy, setSortBy] = useState("TRANSLATOR")

  const fetchData = async (page: number, size: number) => {
    setLoading(true)
    try {
      const apiUrl = `http://localhost:8000/translators?per_page=${pageSize}&page=${pageIndex}&sort_by=${sortBy}&asc=${asc}`
      const response = await fetch(apiUrl)
      const result = await response.json()
      // console.log(response)
      // console.log(result)
      
      setData(result.data)
      setPageCount(result.total_pages)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData(pageIndex, pageSize)
  }, [pageIndex, pageSize])

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>

  return (
    <>
      <DataTable 
        data={data} 
        columns={columns} 
        enableDragAndDrop={false} 
        enableRowSelection={true} 
        pageCount={pageCount} 
        pageSize={pageSize} 
        pageIndex={pageIndex - 1} 
        onPaginationChange={(newPagination) => {
          setPageIndex(newPagination.pageIndex + 1)
          setPageSize(newPagination.pageSize)
        }} 
        manualPagination={true} 
      />
    </>
  )
}
