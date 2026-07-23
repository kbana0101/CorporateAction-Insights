"use client"

import React, { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { supabase } from "@/lib/supabase-client"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    setLoading(false)

    if (error) {
      setError(error.message)
      return
    }

    if (data?.user) {
      router.push("/chat")
    }
  }

  return (
    <div className="flex items-center justify-center h-full">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Sign in</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Email</label>
              <Input value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Password</label>
              <Input value={password} onChange={(e) => setPassword(e.target.value)} type="password" />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <div className="flex items-center justify-between">
              <Button type="submit" disabled={loading}>{loading ? "Signing in..." : "Sign in"}</Button>
              <Link href="/signup" className="text-sm text-muted-foreground">Create account</Link>
            </div>
          </form>
        </CardContent>
        <CardFooter />
      </Card>
    </div>
  )
}
