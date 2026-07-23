"use client"

import React, { useState } from "react"
import { useRouter } from "next/navigation"
import { supabase } from "@/lib/supabase-client"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

export default function SignupPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
    })
    setLoading(false)

    if (error) {
      setError(error.message)
      return
    }

    // Supabase may require email confirmation; redirect to login with notice
    router.push("/login")
  }

  return (
    <div className="flex items-center justify-center h-full">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Create account</CardTitle>
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
              <Button type="submit" disabled={loading}>{loading ? "Creating..." : "Sign up"}</Button>
            </div>
          </form>
        </CardContent>
        <CardFooter />
      </Card>
    </div>
  )
}
